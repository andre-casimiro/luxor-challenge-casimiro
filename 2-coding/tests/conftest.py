"""Shared fixtures: real CoinGecko payloads captured from the live API."""

from __future__ import annotations

import pytest

# Captured from GET /simple/price?ids=bitcoin,ethereum,zcash&vs_currencies=usd&...
SIMPLE_PRICE = {
    "bitcoin": {
        "usd": 61728,
        "usd_market_cap": 1236198604288.4258,
        "usd_24h_vol": 40498530785.50467,
        "usd_24h_change": -2.846390952179392,
        "last_updated_at": 1781046642,
    },
    "ethereum": {
        "usd": 1638.95,
        "usd_market_cap": 197663945203.5905,
        "usd_24h_vol": 14669992083.206783,
        "usd_24h_change": -4.196189093675374,
        "last_updated_at": 1781046644,
    },
    "zcash": {
        "usd": 425.4,
        "usd_market_cap": 7137910990.751318,
        "usd_24h_vol": 958015864.7388973,
        "usd_24h_change": -7.56908162955918,
        "last_updated_at": 1781046643,
    },
}

# Captured from GET /coins/markets?vs_currency=usd&ids=bitcoin,ethereum,zcash (trimmed).
# ethereum.max_supply is null on purpose -- the parser must tolerate it.
COINS_MARKETS = [
    {
        "id": "bitcoin",
        "symbol": "btc",
        "name": "Bitcoin",
        "image": "https://coin-images.coingecko.com/coins/images/1/large/bitcoin.png",
        "max_supply": 21000000.0,
    },
    {
        "id": "ethereum",
        "symbol": "eth",
        "name": "Ethereum",
        "image": "https://coin-images.coingecko.com/coins/images/279/large/ethereum.png",
        "max_supply": None,
    },
    {
        "id": "zcash",
        "symbol": "zec",
        "name": "Zcash",
        "image": "https://coin-images.coingecko.com/coins/images/486/large/zcash.png",
        "max_supply": 21000000.0,
    },
]


@pytest.fixture
def simple_price() -> dict:
    return {k: dict(v) for k, v in SIMPLE_PRICE.items()}


@pytest.fixture
def coins_markets() -> list[dict]:
    return [dict(row) for row in COINS_MARKETS]
