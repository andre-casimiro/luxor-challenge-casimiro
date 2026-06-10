"""Thin CoinGecko REST client.

Two endpoints are used:
  * /simple/price   -> the per-second feed (one batched call for all assets)
  * /coins/markets  -> descriptive metadata to seed the `assets` maestro table
                       (it carries symbol/name, which /simple/price does not)

Parsing is split out into module-level functions so it can be unit-tested against
captured JSON without any network.
"""

from __future__ import annotations

import logging
import time
from datetime import UTC, datetime

import httpx

from .config import Settings, settings
from .models import Asset, Tick

logger = logging.getLogger(__name__)

# Retried on transient failures (rate limit / upstream blips).
_RETRY_STATUS = {429, 502, 503, 504}


def parse_prices(payload: dict, *, vs: str, ingested_at: datetime) -> list[Tick]:
    """Turn a /simple/price response into one Tick per asset.

    Shape: {"bitcoin": {"usd": 1, "usd_market_cap": 2, "usd_24h_vol": 3,
                         "usd_24h_change": 4, "last_updated_at": 169...}}
    """
    ticks: list[Tick] = []
    for asset_id, fields in payload.items():
        price = fields.get(vs)
        if price is None:
            # Unknown id or missing currency -> skip rather than crash the stream.
            logger.warning("no %s price for %s in response", vs, asset_id)
            continue
        last_updated = fields.get("last_updated_at")
        ts = (
            datetime.fromtimestamp(last_updated, tz=UTC)
            if last_updated is not None
            else ingested_at
        )
        ticks.append(
            Tick(
                asset_id=asset_id,
                ts=ts,
                ingested_at=ingested_at,
                price=float(price),
                volume_24h=_opt_float(fields.get(f"{vs}_24h_vol")),
                market_cap=_opt_float(fields.get(f"{vs}_market_cap")),
                change_24h=_opt_float(fields.get(f"{vs}_24h_change")),
            )
        )
    return ticks


def parse_markets(payload: list[dict]) -> list[Asset]:
    """Turn a /coins/markets response into Asset rows."""
    return [
        Asset(
            id=row["id"],
            symbol=row["symbol"],
            name=row["name"],
            image_url=row.get("image"),
            max_supply=_opt_float(row.get("max_supply")),
        )
        for row in payload
    ]


def _opt_float(value: object) -> float | None:
    return None if value is None else float(value)  # type: ignore[arg-type]


class CoinGeckoClient:
    """Synchronous client with simple bounded retry/backoff on transient errors."""

    def __init__(self, cfg: Settings = settings, *, max_retries: int = 3) -> None:
        self._cfg = cfg
        self._max_retries = max_retries
        headers = {"accept": "application/json"}
        if cfg.coingecko_api_key:
            headers["x-cg-demo-api-key"] = cfg.coingecko_api_key
        self._http = httpx.Client(
            base_url=cfg.coingecko_base_url,
            headers=headers,
            timeout=cfg.request_timeout_s,
        )

    def fetch_prices(self) -> list[Tick]:
        vs = self._cfg.vs_currency
        payload = self._get(
            "/simple/price",
            params={
                "ids": ",".join(self._cfg.asset_ids),
                "vs_currencies": vs,
                "include_market_cap": "true",
                "include_24hr_vol": "true",
                "include_24hr_change": "true",
                "include_last_updated_at": "true",
            },
        )
        return parse_prices(payload, vs=vs, ingested_at=datetime.now(tz=UTC))

    def fetch_markets(self) -> list[Asset]:
        payload = self._get(
            "/coins/markets",
            params={
                "vs_currency": self._cfg.vs_currency,
                "ids": ",".join(self._cfg.asset_ids),
                "sparkline": "false",
            },
        )
        return parse_markets(payload)

    def _get(self, path: str, params: dict) -> object:
        last_exc: Exception | None = None
        for attempt in range(self._max_retries):
            try:
                resp = self._http.get(path, params=params)
                if resp.status_code in _RETRY_STATUS:
                    raise httpx.HTTPStatusError(
                        f"retryable status {resp.status_code}",
                        request=resp.request,
                        response=resp,
                    )
                resp.raise_for_status()
                return resp.json()
            except (httpx.HTTPError, httpx.HTTPStatusError) as exc:
                last_exc = exc
                backoff = 0.5 * (2**attempt)  # 0.5s, 1s, 2s
                # DEBUG, not WARNING: retries are expected (esp. 429s) and would
                # otherwise flood the logs. The caller decides how to report a
                # poll that fails all retries.
                logger.debug(
                    "GET %s failed (attempt %d/%d): %s -- retrying in %.1fs",
                    path, attempt + 1, self._max_retries, exc, backoff,
                )
                time.sleep(backoff)
        assert last_exc is not None
        raise last_exc

    def close(self) -> None:
        self._http.close()
