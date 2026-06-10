"""Parsing tests: captured JSON -> Tick / Asset (no network)."""

from __future__ import annotations

from datetime import UTC, datetime

from crypto_feed.coingecko import parse_markets, parse_prices

INGESTED = datetime(2026, 6, 9, 23, 0, 0, tzinfo=UTC)


def test_parse_prices_maps_all_assets(simple_price):
    ticks = {t.asset_id: t for t in parse_prices(simple_price, vs="usd", ingested_at=INGESTED)}

    assert set(ticks) == {"bitcoin", "ethereum", "zcash"}
    btc = ticks["bitcoin"]
    assert btc.price == 61728
    assert btc.volume_24h == 40498530785.50467
    assert btc.market_cap == 1236198604288.4258
    assert btc.change_24h == -2.846390952179392


def test_parse_prices_uses_source_timestamp(simple_price):
    ticks = {t.asset_id: t for t in parse_prices(simple_price, vs="usd", ingested_at=INGESTED)}

    # ts comes from last_updated_at (source event time), not our poll wall-clock.
    assert ticks["bitcoin"].ts == datetime.fromtimestamp(1781046642, tz=UTC)
    assert ticks["bitcoin"].ingested_at == INGESTED


def test_parse_prices_falls_back_to_ingested_when_no_source_ts():
    payload = {"bitcoin": {"usd": 100.0}}  # no last_updated_at
    (tick,) = parse_prices(payload, vs="usd", ingested_at=INGESTED)
    assert tick.ts == INGESTED
    assert tick.volume_24h is None


def test_parse_prices_skips_assets_missing_currency():
    payload = {"bitcoin": {"eur": 100.0}}  # asked for usd, only eur present
    assert parse_prices(payload, vs="usd", ingested_at=INGESTED) == []


def test_parse_markets_tolerates_null_max_supply(coins_markets):
    assets = {a.id: a for a in parse_markets(coins_markets)}

    assert assets["bitcoin"].symbol == "btc"
    assert assets["bitcoin"].max_supply == 21000000.0
    assert assets["ethereum"].max_supply is None  # ETH has no cap
    assert assets["zcash"].name == "Zcash"
