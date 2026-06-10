"""Bytewax input source: poll CoinGecko once per `interval`.

`SimplePollingSource` handles the timing (it calls `next_item` on a fixed cadence
and is the idiomatic way to wrap a pull-based API). Each poll returns the batch of
ticks for that second; the dataflow then flat-maps the batch into individual ticks.
"""

from __future__ import annotations

import logging
from datetime import timedelta

from bytewax.inputs import SimplePollingSource

from .coingecko import CoinGeckoClient
from .config import settings
from .models import Tick

logger = logging.getLogger(__name__)


class CoinGeckoSource(SimplePollingSource):
    """Emits one `list[Tick]` per poll (all configured assets in a single call)."""

    def __init__(self, interval_s: float = settings.poll_interval_s) -> None:
        super().__init__(interval=timedelta(seconds=interval_s))
        self._client = CoinGeckoClient()

    def next_item(self) -> list[Tick]:
        try:
            return self._client.fetch_prices()
        except Exception:  # noqa: BLE001 -- never let one bad poll kill the stream
            logger.exception("poll failed; skipping this tick")
            return []
