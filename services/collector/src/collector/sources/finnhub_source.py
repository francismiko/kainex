from __future__ import annotations

import asyncio
from datetime import datetime, timezone

import finnhub

from collector.config import settings
from collector.models.bar import Bar, Market, TimeFrame

from .base import AbstractDataSource

_RESOLUTION_MAP = {
    TimeFrame.M1: "1",
    TimeFrame.M5: "5",
    TimeFrame.M15: "15",
    TimeFrame.H1: "60",
    TimeFrame.D1: "D",
    TimeFrame.W1: "W",
}


class FinnhubSource(AbstractDataSource):
    """Finnhub US stock data source (free tier: 60 calls/min)."""

    def __init__(self, api_key: str | None = None) -> None:
        self._api_key = api_key or settings.finnhub_api_key
        self._client = finnhub.Client(api_key=self._api_key)

    @property
    def market(self) -> Market:
        return Market.US_STOCK

    async def fetch_bars(
        self,
        symbol: str,
        timeframe: TimeFrame,
        start: datetime,
        end: datetime,
    ) -> list[Bar]:
        resolution = _RESOLUTION_MAP.get(timeframe, "D")
        start_ts = int(start.timestamp())
        end_ts = int(end.timestamp())

        data = await asyncio.to_thread(
            self._client.stock_candles,
            symbol,
            resolution,
            start_ts,
            end_ts,
        )

        if data.get("s") != "ok":
            raise ValueError(f"Finnhub returned no data for {symbol}: {data.get('s')}")

        bars: list[Bar] = []
        for i in range(len(data["t"])):
            bars.append(
                Bar(
                    symbol=symbol,
                    market=Market.US_STOCK,
                    timeframe=timeframe,
                    open=float(data["o"][i]),
                    high=float(data["h"][i]),
                    low=float(data["l"][i]),
                    close=float(data["c"][i]),
                    volume=float(data["v"][i]),
                    timestamp=datetime.fromtimestamp(data["t"][i], tz=timezone.utc),
                )
            )
        return bars

    async def fetch_latest_bar(
        self,
        symbol: str,
        timeframe: TimeFrame,
    ) -> Bar:
        quote = await asyncio.to_thread(self._client.quote, symbol)

        if not quote or quote.get("c") is None or quote.get("c") == 0:
            raise ValueError(f"Finnhub returned no quote for {symbol}")

        return Bar(
            symbol=symbol,
            market=Market.US_STOCK,
            timeframe=timeframe,
            open=float(quote["o"]),
            high=float(quote["h"]),
            low=float(quote["l"]),
            close=float(quote["c"]),
            volume=0.0,  # quote endpoint does not return volume
            timestamp=datetime.fromtimestamp(quote["t"], tz=timezone.utc),
        )
