"""The Bytewax dataflow: poll -> fan-out to (A) Postgres and (B) the alert window.

Run with:  python -m bytewax.run crypto_feed.dataflow:flow

This is the push-based design the challenge asks for: a polled tick is pushed
through the graph and branched to persistence and alerting in the same process.
Nothing reads back from the database to produce alerts.

    CoinGeckoSource (1/s)
            |
        flat_map  (batch -> individual ticks)
          /   \\
   PostgresSink  key_on(asset) -> stateful_map(RollingWindowDetector)
   (branch A)              |
                      flat_map (-> individual alerts)
                        /      \\
               AlertFileSink   StdOutSink
                (branch B: alerts.txt + console)
"""

from __future__ import annotations

import logging

import bytewax.operators as op
from bytewax.connectors.stdio import StdOutSink
from bytewax.dataflow import Dataflow

from .alerting import RollingWindowDetector
from .config import settings
from .models import Alert, Tick
from .sinks import AlertFileSink, PostgresSink
from .sources import CoinGeckoSource

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s"
)


def _detect(
    state: RollingWindowDetector | None, tick: Tick
) -> tuple[RollingWindowDetector, list[Alert]]:
    """stateful_map accumulator: one detector per asset, updated per tick."""
    if state is None:
        state = RollingWindowDetector(
            window_s=settings.alert_window_s,
            threshold=settings.alert_threshold,
            warmup_s=settings.alert_warmup_s,
        )
    return state, state.update(tick)


def _format(alert: Alert) -> str:
    arrow = "▲" if alert.change_pct > 0 else "▼"
    return (
        f"ALERT {arrow} {alert.asset_id} {alert.metric} "
        f"{alert.change_pct:+.2%} vs {alert.window_s // 60}m avg "
        f"(value={alert.value:.4g}, baseline={alert.baseline:.4g}, n={alert.samples})"
    )


def build_flow() -> Dataflow:
    flow = Dataflow("crypto-feed")

    batches = op.input("coingecko", flow, CoinGeckoSource())
    ticks = op.flat_map("split-batch", batches, lambda batch: batch)

    # Branch A: persist every tick.
    op.output("postgres", ticks, PostgresSink())

    # Branch B: per-asset trailing-window alerting.
    keyed = op.key_on("by-asset", ticks, lambda t: t.asset_id)
    keyed_alerts = op.stateful_map("roll-5m", keyed, _detect)
    alerts = op.flat_map("explode-alerts", keyed_alerts, lambda kv: kv[1])

    op.output("alert-file", alerts, AlertFileSink())
    op.output("alert-stdout", op.map("fmt", alerts, _format), StdOutSink())

    return flow


flow = build_flow()
