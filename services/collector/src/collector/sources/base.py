from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from collections.abc import Callable, Coroutine
from datetime import datetime
from typing import Any

from collector.models.bar import Bar, Market, TimeFrame
from collector.models.tick import Tick

logger = logging.getLogger(__name__)


class AbstractDataSource(ABC):
    @property
    @abstractmethod
    def market(self) -> Market: ...

    @abstractmethod
    async def fetch_bars(
        self,
        symbol: str,
        timeframe: TimeFrame,
        start: datetime,
        end: datetime,
    ) -> list[Bar]: ...

    @abstractmethod
    async def fetch_latest_bar(
        self,
        symbol: str,
        timeframe: TimeFrame,
    ) -> Bar: ...

    async def subscribe_realtime(
        self,
        symbols: list[str],
        callback: Callable[[Tick], Coroutine[Any, Any, None]],
    ) -> None:
        raise NotImplementedError(
            f"{self.__class__.__name__} does not support realtime subscription"
        )


class DataSourceManager:
    """Manages multiple data sources with automatic fallback."""

    def __init__(self, sources: list[AbstractDataSource]) -> None:
        self._sources = sources

    async def fetch_bars(
        self,
        symbol: str,
        timeframe: TimeFrame,
        start: datetime,
        end: datetime,
    ) -> list[Bar]:
        last_error: Exception | None = None
        for source in self._sources:
            try:
                return await source.fetch_bars(symbol, timeframe, start, end)
            except Exception as e:
                logger.warning(
                    "%s failed for %s: %s, trying next...",
                    source.__class__.__name__,
                    symbol,
                    e,
                )
                last_error = e
        raise RuntimeError(f"All data sources failed for {symbol}") from last_error

    async def fetch_latest_bar(
        self,
        symbol: str,
        timeframe: TimeFrame,
    ) -> Bar:
        last_error: Exception | None = None
        for source in self._sources:
            try:
                return await source.fetch_latest_bar(symbol, timeframe)
            except Exception as e:
                logger.warning(
                    "%s failed for %s: %s, trying next...",
                    source.__class__.__name__,
                    symbol,
                    e,
                )
                last_error = e
        raise RuntimeError(f"All data sources failed for {symbol}") from last_error
