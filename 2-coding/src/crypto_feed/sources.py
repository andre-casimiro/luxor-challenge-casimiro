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
        self._skipped = 0  # consecutive failed polls (for de-duplicated logging)

    def next_item(self) -> list[Tick]:
        try:
            ticks = self._client.fetch_prices()
        except Exception as exc:  # noqa: BLE001 -- never let one bad poll kill the stream
            # Sustained failures (typically 429 rate limiting) are expected, so log
            # once when the feed starts degrading and stay quiet while it persists.
            if self._skipped == 0:
                logger.warning("feed degraded (%s); skipping polls until it recovers", exc)
            self._skipped += 1
            return []

        if self._skipped:
            logger.info("feed recovered after %d skipped poll(s)", self._skipped)
            self._skipped = 0
        return ticks
