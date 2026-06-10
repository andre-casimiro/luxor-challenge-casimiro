"""Bytewax output sinks.

Two custom `DynamicSink`s:
  * PostgresSink   -- persists ticks to the `ohlcv` hypertable (branch A)
  * AlertFileSink  -- appends alerts as JSON lines to a .txt file (branch B)

A `DynamicSink` builds one `StatelessSinkPartition` per worker; `write_batch` is
called with the items Bytewax has buffered for that step. We run a single worker,
so one partition handles everything.
"""

from __future__ import annotations

import json
import logging
from collections.abc import Iterable

import psycopg
from bytewax.outputs import DynamicSink, StatelessSinkPartition

from .config import settings
from .models import Alert, Tick

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Postgres / TimescaleDB
# ---------------------------------------------------------------------------
_INSERT_SQL = """
    INSERT INTO ohlcv (asset_id, ts, ingested_at, price, volume_24h, market_cap, change_24h)
    VALUES (%(asset_id)s, %(ts)s, %(ingested_at)s, %(price)s, %(volume_24h)s,
            %(market_cap)s, %(change_24h)s)
    ON CONFLICT (asset_id, ingested_at) DO NOTHING
"""


class _PostgresPartition(StatelessSinkPartition):
    def __init__(self, dsn: str) -> None:
        # autocommit: each per-second batch is durably written immediately.
        self._conn = psycopg.connect(dsn, autocommit=True)

    def write_batch(self, items: list[Tick]) -> None:
        if not items:
            return
        rows = [
            {
                "asset_id": t.asset_id,
                "ts": t.ts,
                "ingested_at": t.ingested_at,
                "price": t.price,
                "volume_24h": t.volume_24h,
                "market_cap": t.market_cap,
                "change_24h": t.change_24h,
            }
            for t in items
        ]
        with self._conn.cursor() as cur:
            cur.executemany(_INSERT_SQL, rows)

    def close(self) -> None:
        self._conn.close()


class PostgresSink(DynamicSink):
    def __init__(self, dsn: str = settings.db_dsn) -> None:
        self._dsn = dsn

    def build(self, step_id: str, worker_index: int, worker_count: int):
        return _PostgresPartition(self._dsn)


# ---------------------------------------------------------------------------
# Alert file (JSON lines)
# ---------------------------------------------------------------------------
class _AlertFilePartition(StatelessSinkPartition):
    def __init__(self, path: str) -> None:
        self._fh = open(path, "a", encoding="utf-8")  # noqa: SIM115 -- closed in close()

    def write_batch(self, items: Iterable[Alert]) -> None:
        wrote = False
        for alert in items:
            self._fh.write(json.dumps(alert.to_dict()) + "\n")
            wrote = True
        if wrote:
            self._fh.flush()

    def close(self) -> None:
        self._fh.close()


class AlertFileSink(DynamicSink):
    def __init__(self, path: str = settings.alert_file) -> None:
        self._path = path

    def build(self, step_id: str, worker_index: int, worker_count: int):
        return _AlertFilePartition(self._path)
