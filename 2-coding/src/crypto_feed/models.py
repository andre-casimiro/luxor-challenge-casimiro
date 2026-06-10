"""Plain data carriers that flow through the dataflow.

Kept as frozen dataclasses (no I/O, no framework types) so they are trivial to
construct in tests and cheap to pass between Bytewax operators.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True, slots=True)
class Asset:
    """A row of the `assets` maestro table (descriptive metadata)."""

    id: str            # CoinGecko id, e.g. "bitcoin"
    symbol: str        # "btc"
    name: str          # "Bitcoin"
    image_url: str | None = None
    max_supply: float | None = None


@dataclass(frozen=True, slots=True)
class Tick:
    """One price reading for one asset at one instant (a snapshot, not a candle)."""

    asset_id: str
    ts: datetime           # source event time (CoinGecko last_updated_at)
    ingested_at: datetime  # our poll wall-clock time
    price: float
    volume_24h: float | None = None
    market_cap: float | None = None
    change_24h: float | None = None


@dataclass(frozen=True, slots=True)
class Alert:
    """Emitted when a tick deviates from its trailing-window baseline."""

    asset_id: str
    metric: str            # "price" or "volume"
    value: float           # the triggering reading
    baseline: float        # trailing-window average it was compared against
    change_pct: float      # signed deviation, e.g. -0.034 == -3.4%
    threshold: float       # configured threshold that was crossed
    window_s: int          # length of the baseline window
    samples: int           # number of readings in the baseline
    ts: datetime           # tick source time

    def to_dict(self) -> dict:
        return {
            "asset_id": self.asset_id,
            "metric": self.metric,
            "value": self.value,
            "baseline": self.baseline,
            "change_pct": round(self.change_pct, 6),
            "threshold": self.threshold,
            "window_s": self.window_s,
            "samples": self.samples,
            "ts": self.ts.isoformat(),
        }
