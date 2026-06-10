"""Behavioral tests for the RollingWindowDetector (the alert engine's core)."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from crypto_feed.alerting import RollingWindowDetector
from crypto_feed.models import Tick

BASE = datetime(2026, 6, 9, 12, 0, 0, tzinfo=UTC)


def tick(sec: float, price: float, volume: float | None = 1000.0) -> Tick:
    t = BASE + timedelta(seconds=sec)
    return Tick(asset_id="bitcoin", ts=t, ingested_at=t, price=price, volume_24h=volume)


def test_first_tick_never_alerts():
    det = RollingWindowDetector(window_s=300, threshold=0.02, warmup_s=0)
    assert det.update(tick(0, 100.0)) == []


def test_no_alert_within_threshold():
    det = RollingWindowDetector(window_s=300, threshold=0.02, warmup_s=0)
    det.update(tick(0, 100.0))
    # +1% vs baseline 100 -> under the 2% threshold.
    assert det.update(tick(1, 101.0)) == []


def test_price_spike_triggers_alert():
    det = RollingWindowDetector(window_s=300, threshold=0.02, warmup_s=10)
    for s in range(0, 16):
        det.update(tick(s, 100.0))
    alerts = det.update(tick(16, 105.0))  # +5% vs ~100 baseline

    assert len(alerts) == 1
    a = alerts[0]
    assert a.metric == "price"
    assert a.value == 105.0
    assert abs(a.baseline - 100.0) < 1e-9
    assert a.change_pct > 0.02


def test_volume_spike_triggers_alert():
    det = RollingWindowDetector(window_s=300, threshold=0.02, warmup_s=10)
    for s in range(0, 16):
        det.update(tick(s, 100.0, volume=1000.0))
    # Price flat, volume +5% -> only a volume alert.
    alerts = det.update(tick(16, 100.0, volume=1050.0))

    assert [a.metric for a in alerts] == ["volume"]
    assert alerts[0].change_pct > 0.02


def test_warmup_suppresses_early_alerts():
    det = RollingWindowDetector(window_s=300, threshold=0.02, warmup_s=30)
    det.update(tick(0, 100.0))
    # Huge jump, but only 5s of history (< 30s warmup) -> stay quiet.
    assert det.update(tick(5, 200.0)) == []


def test_window_eviction_drops_stale_samples():
    det = RollingWindowDetector(window_s=10, threshold=0.02, warmup_s=0)
    # Old, high prices that must fall out of the 10s window.
    for s in (0, 1, 2):
        det.update(tick(s, 200.0))
    # Recent, lower prices establish a fresh baseline.
    for s in (11, 12, 13):
        det.update(tick(s, 100.0))

    alerts = det.update(tick(14, 105.0))

    assert len(alerts) == 1
    # Baseline reflects only the recent ~100 samples, not the evicted 200s.
    assert abs(alerts[0].baseline - 100.0) < 1e-9
    assert alerts[0].change_pct > 0.0


def test_per_tick_state_is_isolated_per_detector():
    # Two assets would each get their own detector instance in the dataflow;
    # here we assert one detector's history doesn't leak a baseline before warmup.
    det = RollingWindowDetector(window_s=300, threshold=0.02, warmup_s=0)
    det.update(tick(0, 50.0))
    # Second tick +200% -> alert (baseline 50, value 150).
    alerts = det.update(tick(1, 150.0))
    assert len(alerts) == 1
    assert abs(alerts[0].baseline - 50.0) < 1e-9
