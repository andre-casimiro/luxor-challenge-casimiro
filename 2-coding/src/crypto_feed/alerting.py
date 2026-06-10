"""Trailing-window deviation detector -- the heart of the alert system.

This is the accumulator that Bytewax's `op.stateful_map` drives: the dataflow keys
ticks by asset and keeps exactly one detector instance per key as managed state, so
this class only ever sees one asset's stream. It performs the streaming rollup (the
trailing 5-minute average) and the comparison, all push-based -- each incoming tick
is checked against the running baseline and may immediately emit an alert. Nothing
polls the database.

Detection rule (from the challenge):
    fire when price or volume changes by more than `threshold` (2%) from the
    trailing `window` (5-minute) average.

Kept pure (no I/O, no Bytewax types) so it is trivial to unit-test.
"""

from __future__ import annotations

from collections import deque
from datetime import datetime, timedelta

from .models import Alert, Tick


class RollingWindowDetector:
    """Maintains a trailing window of (price, volume) for one asset."""

    def __init__(
        self,
        *,
        window_s: int,
        threshold: float,
        warmup_s: int = 0,
    ) -> None:
        self._window = timedelta(seconds=window_s)
        self._window_s = window_s
        self._threshold = threshold
        self._warmup = timedelta(seconds=warmup_s)
        # (ts, price, volume) ordered oldest -> newest.
        self._samples: deque[tuple[datetime, float, float | None]] = deque()

    def update(self, tick: Tick) -> list[Alert]:
        """Record a tick and return any alerts it triggers (price and/or volume).

        The baseline is the window *before* this tick, so a tick is never compared
        against itself: we evict + average first, then append.
        """
        self._evict(tick.ts)
        alerts: list[Alert] = []

        if self._ready(tick.ts):
            alerts.extend(self._check("price", tick.price, tick))
            if tick.volume_24h is not None:
                alerts.extend(self._check("volume", tick.volume_24h, tick))

        self._samples.append((tick.ts, tick.price, tick.volume_24h))
        return alerts

    # -- internals ----------------------------------------------------------
    def _evict(self, now: datetime) -> None:
        cutoff = now - self._window
        while self._samples and self._samples[0][0] < cutoff:
            self._samples.popleft()

    def _ready(self, now: datetime) -> bool:
        """Enough history to trust the baseline? Avoids alerting on the first ticks."""
        if not self._samples:
            return False
        span = now - self._samples[0][0]
        return span >= self._warmup

    def _check(self, metric: str, value: float, tick: Tick) -> list[Alert]:
        baseline = self._average(index=1 if metric == "price" else 2)
        if baseline is None or baseline == 0:
            return []
        change = (value - baseline) / baseline
        if abs(change) <= self._threshold:
            return []
        return [
            Alert(
                asset_id=tick.asset_id,
                metric=metric,
                value=value,
                baseline=baseline,
                change_pct=change,
                threshold=self._threshold,
                window_s=self._window_s,
                samples=len(self._samples),
                ts=tick.ts,
            )
        ]

    def _average(self, *, index: int) -> float | None:
        vals = [s[index] for s in self._samples if s[index] is not None]
        return sum(vals) / len(vals) if vals else None
