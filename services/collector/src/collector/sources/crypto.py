import asyncio
from collections.abc import Callable, Coroutine
from datetime import datetime, timezone
from typing import Any

import ccxt.async_support as ccxt_async

from collector.models.bar import Bar, Market, TimeFrame
from collector.models.tick import Tick

from .base import AbstractDataSource


class CryptoSource(AbstractDataSource):
    def __init__(self, exchange_id: str = "binance") -> None:
        self._exchange_id = exchange_id

    @property
    def market(self) -> Market:
        return Market.CRYPTO

    def _create_exchange(self) -> ccxt_async.Exchange:
        cls = getattr(ccxt_async, self._exchange_id)
        return cls({"enableRateLimit": True})

    async def fetch_bars(
        self,
        symbol: str,
        timeframe: TimeFrame,
        start: datetime,
        end: datetime,
    ) -> list[Bar]:
        exchange = self._create_exchange()
        try:
            since = int(start.timestamp() * 1000)
            ohlcv = await exchange.fetch_ohlcv(symbol, timeframe.value, since=since)
        finally:
            await exchange.close()

        end_ts = end.timestamp() * 1000
        bars: list[Bar] = []
        for candle in ohlcv:
            if candle[0] > end_ts:
                break
            bars.append(
                Bar(
                    symbol=symbol,
                    market=Market.CRYPTO,
                    timeframe=timeframe,
                    open=candle[1],
                    high=candle[2],
                    low=candle[3],
                    close=candle[4],
                    volume=candle[5],
                    timestamp=datetime.fromtimestamp(candle[0] / 1000, tz=timezone.utc),
                )
            )
        return bars

    async def fetch_latest_bar(
        self,
        symbol: str,
        timeframe: TimeFrame,
    ) -> Bar:
        exchange = self._create_exchange()
        try:
            ohlcv = await exchange.fetch_ohlcv(symbol, timeframe.value, limit=1)
        finally:
            await exchange.close()

        if not ohlcv:
            raise ValueError(f"No data available for {symbol}")
        candle = ohlcv[-1]
        return Bar(
            symbol=symbol,
            market=Market.CRYPTO,
            timeframe=timeframe,
            open=candle[1],
            high=candle[2],
            low=candle[3],
            close=candle[4],
            volume=candle[5],
            timestamp=datetime.fromtimestamp(candle[0] / 1000, tz=timezone.utc),
        )

    async def subscribe_realtime(
        self,
        symbols: list[str],
        callback: Callable[[Tick], Coroutine[Any, Any, None]],
        stop_event: asyncio.Event | None = None,
    ) -> None:
        """Subscribe to real-time ticker updates for the given symbols.

        .. note::
            Current implementation uses REST polling (fetch_ticker) as a
            placeholder.  For true real-time streaming with lower latency and
            reduced rate-limit pressure, migrate to ``ccxt.pro``'s
            ``watch_ticker`` WebSocket API::

                async for ticker in exchange.watch_ticker(symbol):
                    ...

        Args:
            symbols: List of trading pair symbols (e.g. ``["BTC/USDT"]``).
            callback: Async callable invoked with each new ``Tick``.
            stop_event: Optional :class:`asyncio.Event`. When set, the
                polling loop exits gracefully.  If *None*, the loop runs
                until cancelled externally.
        """
        exchange = self._create_exchange()
        try:
            while not (stop_event and stop_event.is_set()):
                for symbol in symbols:
                    ticker = await exchange.fetch_ticker(symbol)
                    tick = Tick(
                        symbol=symbol,
                        market=Market.CRYPTO,
                        price=ticker["last"],
                        volume=ticker["baseVolume"] or 0.0,
                        bid=ticker["bid"] or 0.0,
                        ask=ticker["ask"] or 0.0,
                        timestamp=datetime.fromtimestamp(
                            ticker["timestamp"] / 1000, tz=timezone.utc
                        ),
                    )
                    await callback(tick)
                try:
                    await asyncio.wait_for(
                        stop_event.wait() if stop_event else asyncio.sleep(1),
                        timeout=1,
                    )
                except TimeoutError:
                    pass
        finally:
            await exchange.close()
