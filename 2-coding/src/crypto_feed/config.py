"""Runtime configuration, loaded from environment variables (and an optional .env).

Everything tunable lives here so the tool can be pointed at new assets, thresholds
or windows without touching code -- see the README's "Extension" section.
"""

from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_prefix="", extra="ignore")

    # --- Database -----------------------------------------------------------
    database_url: str = "postgresql://crypto:crypto@localhost:15432/crypto"

    # --- CoinGecko ----------------------------------------------------------
    # CoinGecko ids (not symbols). /simple/price is keyed by these.
    asset_ids: list[str] = ["bitcoin", "ethereum", "zcash"]
    vs_currency: str = "usd"
    # Optional demo/pro API key. The free public API caps at ~30 calls/min, below
    # our 60 calls/min; with a key the limit is high enough for a true 1s cadence.
    coingecko_api_key: str | None = None
    coingecko_base_url: str = "https://api.coingecko.com/api/v3"
    request_timeout_s: float = 10.0

    # --- Polling ------------------------------------------------------------
    poll_interval_s: float = 1.0

    # --- Alerting -----------------------------------------------------------
    alert_window_s: int = 300          # trailing window for the baseline average (5 min)
    alert_threshold: float = 0.02      # fire when |value - avg| / avg exceeds this (2%)
    alert_warmup_s: int = 30           # don't alert until the window has this much history
    alert_file: str = "alerts.txt"

    @property
    def db_dsn(self) -> str:
        """psycopg accepts the SQLAlchemy-style URL as-is."""
        return self.database_url


settings = Settings()
