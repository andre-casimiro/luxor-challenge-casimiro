-- Schema for the CoinGecko feed.
--
-- Two tables, as recommended by the challenge:
--   * assets  -- "maestro" of digital assets: slow-changing descriptive metadata
--   * ohlcv   -- historical feed: one raw tick per asset per poll (high volume)
--
-- The statements are idempotent (IF NOT EXISTS) so bootstrap can run them on every
-- start. bootstrap.py executes them one at a time in autocommit mode because some
-- TimescaleDB statements (continuous aggregates, policies) cannot run inside a
-- transaction block.

CREATE EXTENSION IF NOT EXISTS timescaledb;

-- ---------------------------------------------------------------------------
-- Maestro of digital assets
-- ---------------------------------------------------------------------------
-- Seeded once from /coins/markets, which (unlike /simple/price) carries symbol
-- and name. Refreshed on every bootstrap via UPSERT.
CREATE TABLE IF NOT EXISTS assets (
    id         text PRIMARY KEY,       -- CoinGecko id, e.g. 'bitcoin'
    symbol     text NOT NULL,          -- 'btc'
    name       text NOT NULL,          -- 'Bitcoin'
    image_url  text,
    max_supply numeric,                -- nullable (ETH has no max supply)
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now()
);

-- ---------------------------------------------------------------------------
-- Historical feed (raw per-second ticks)
-- ---------------------------------------------------------------------------
-- A single CoinGecko reading is a *tick* (a price snapshot), not a candle, so at
-- 1s granularity O=H=L=C=price would be degenerate. We therefore store the raw
-- tick (price + the rolling 24h volume the API exposes) and derive real OHLCV
-- candles in the continuous aggregates below.
CREATE TABLE IF NOT EXISTS ohlcv (
    asset_id    text        NOT NULL REFERENCES assets (id),
    ts          timestamptz NOT NULL,   -- source event time (last_updated_at)
    ingested_at timestamptz NOT NULL,   -- our poll wall-clock time
    price       numeric     NOT NULL,
    volume_24h  numeric,                -- rolling 24h USD volume (API limitation)
    market_cap  numeric,
    change_24h  numeric,                -- rolling 24h % change
    PRIMARY KEY (asset_id, ingested_at)
);

-- Partition the feed by time. Each chunk holds 1 day of data; old chunks can be
-- compressed / dropped independently, and time-bounded queries prune to a few
-- chunks instead of scanning the whole table.
SELECT create_hypertable('ohlcv', 'ingested_at',
                         chunk_time_interval => INTERVAL '1 day',
                         if_not_exists => TRUE);

-- Newest-first lookups per asset ("last price", recent window) hit this index.
CREATE INDEX IF NOT EXISTS ohlcv_asset_time_idx ON ohlcv (asset_id, ingested_at DESC);

-- ---------------------------------------------------------------------------
-- Derived OHLCV candles (continuous aggregates)
-- ---------------------------------------------------------------------------
-- These are the "real" candles: open/high/low/close computed by aggregating the
-- raw ticks into time buckets. TimescaleDB keeps them incrementally up to date.
-- Dashboards and the 5-minute alert baseline read these small tables instead of
-- scanning millions of raw rows -> the retrieval-speed answer.
-- materialized_only = false enables real-time aggregation (materialized history +
-- the most recent, not-yet-materialized ticks) so queries are never stale.

CREATE MATERIALIZED VIEW IF NOT EXISTS ohlcv_1m
WITH (timescaledb.continuous, timescaledb.materialized_only = false) AS
SELECT asset_id,
       time_bucket(INTERVAL '1 minute', ingested_at) AS bucket,
       first(price, ingested_at) AS open,
       max(price)                AS high,
       min(price)                AS low,
       last(price, ingested_at)  AS close,
       last(volume_24h, ingested_at) AS volume_24h,
       count(*)                  AS ticks
FROM ohlcv
GROUP BY asset_id, bucket
WITH NO DATA;

CREATE MATERIALIZED VIEW IF NOT EXISTS ohlcv_5m
WITH (timescaledb.continuous, timescaledb.materialized_only = false) AS
SELECT asset_id,
       time_bucket(INTERVAL '5 minutes', ingested_at) AS bucket,
       first(price, ingested_at) AS open,
       max(price)                AS high,
       min(price)                AS low,
       last(price, ingested_at)  AS close,
       last(volume_24h, ingested_at) AS volume_24h,
       count(*)                  AS ticks
FROM ohlcv
GROUP BY asset_id, bucket
WITH NO DATA;

-- Refresh policies: keep the candles current automatically.
SELECT add_continuous_aggregate_policy('ohlcv_1m',
    start_offset      => INTERVAL '1 hour',
    end_offset        => INTERVAL '1 minute',
    schedule_interval => INTERVAL '1 minute',
    if_not_exists     => TRUE);

SELECT add_continuous_aggregate_policy('ohlcv_5m',
    start_offset      => INTERVAL '3 hours',
    end_offset        => INTERVAL '5 minutes',
    schedule_interval => INTERVAL '5 minutes',
    if_not_exists     => TRUE);

-- ---------------------------------------------------------------------------
-- Compression (scalability "without losing information")
-- ---------------------------------------------------------------------------
-- Columnar compression of chunks older than 7 days. Lossless: the raw ticks are
-- still queryable, just ~10x smaller. This keeps full history affordable instead
-- of deleting it.
ALTER TABLE ohlcv SET (
    timescaledb.compress,
    timescaledb.compress_segmentby = 'asset_id',
    timescaledb.compress_orderby   = 'ingested_at DESC'
);
SELECT add_compression_policy('ohlcv', INTERVAL '7 days', if_not_exists => TRUE);

-- Optional retention (drop raw ticks older than N days while candles live on).
-- Left disabled because the challenge asks to scale *without losing information*;
-- enable only if raw-tick history is no longer needed:
-- SELECT add_retention_policy('ohlcv', INTERVAL '90 days', if_not_exists => TRUE);
