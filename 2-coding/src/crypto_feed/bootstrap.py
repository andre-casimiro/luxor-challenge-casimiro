"""One-shot setup: apply the schema and seed the `assets` maestro table.

Run before the dataflow (Makefile `seed` target, or `python -m crypto_feed.bootstrap`).
Idempotent: the DDL uses IF NOT EXISTS and the asset seed is an UPSERT.
"""

from __future__ import annotations

import logging
from pathlib import Path

import psycopg

from .coingecko import CoinGeckoClient
from .config import settings
from .models import Asset

logger = logging.getLogger(__name__)

SCHEMA_PATH = Path(__file__).resolve().parents[2] / "db" / "schema.sql"

_UPSERT_ASSET = """
    INSERT INTO assets (id, symbol, name, image_url, max_supply)
    VALUES (%(id)s, %(symbol)s, %(name)s, %(image_url)s, %(max_supply)s)
    ON CONFLICT (id) DO UPDATE SET
        symbol = EXCLUDED.symbol,
        name = EXCLUDED.name,
        image_url = EXCLUDED.image_url,
        max_supply = EXCLUDED.max_supply,
        updated_at = now()
"""


def _split_statements(sql: str) -> list[str]:
    """Split schema.sql into individual statements.

    Some TimescaleDB statements (continuous aggregates, policies) cannot run inside
    a transaction block, so we execute them one at a time in autocommit mode rather
    than sending the whole file as one implicit transaction. The schema deliberately
    uses no dollar-quoted bodies, so splitting on ';' is safe.
    """
    # Strip `--` line comments first so a ';' inside a comment doesn't split a
    # statement (the schema has no dollar-quoted bodies or string literals with '--').
    no_comments = "\n".join(line.split("--", 1)[0] for line in sql.splitlines())
    return [stmt.strip() for stmt in no_comments.split(";") if stmt.strip()]


def apply_schema(conn: psycopg.Connection) -> None:
    sql = SCHEMA_PATH.read_text(encoding="utf-8")
    with conn.cursor() as cur:
        for stmt in _split_statements(sql):
            cur.execute(stmt)
    logger.info("schema applied from %s", SCHEMA_PATH)


def seed_assets(conn: psycopg.Connection, assets: list[Asset]) -> None:
    rows = [
        {
            "id": a.id,
            "symbol": a.symbol,
            "name": a.name,
            "image_url": a.image_url,
            "max_supply": a.max_supply,
        }
        for a in assets
    ]
    with conn.cursor() as cur:
        cur.executemany(_UPSERT_ASSET, rows)
    logger.info("seeded %d assets", len(rows))


def main() -> None:
    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s"
    )
    client = CoinGeckoClient()
    try:
        assets = client.fetch_markets()
    finally:
        client.close()

    # autocommit so TimescaleDB statements that forbid transaction blocks succeed.
    with psycopg.connect(settings.db_dsn, autocommit=True) as conn:
        apply_schema(conn)
        seed_assets(conn, assets)
    logger.info("bootstrap complete: %s", ", ".join(a.id for a in assets))


if __name__ == "__main__":
    main()
