import asyncio
from datetime import datetime, timezone

import yfinance as yf

from collector.models.bar import Bar, Market, TimeFrame

from .base import AbstractDataSource

_YF_INTERVAL_MAP = {
    TimeFrame.M1: "1m",
    TimeFrame.M5: "5m",
    TimeFrame.M15: "15m",
    TimeFrame.H1: "1h",
    TimeFrame.D1: "1d",
    TimeFrame.W1: "1wk",
}


class USStockSource(AbstractDataSource):
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
        interval = _YF_INTERVAL_MAP.get(timeframe, "1d")
        ticker = yf.Ticker(symbol)
        df = await asyncio.to_thread(
            ticker.history,
            interval=interval,
            start=start.strftime("%Y-%m-%d"),
            end=end.strftime("%Y-%m-%d"),
        )

        bars: list[Bar] = []
        for ts, row in df.iterrows():
            dt = ts.to_pydatetime()
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            bars.append(
                Bar(
                    symbol=symbol,
                    market=Market.US_STOCK,
                    timeframe=timeframe,
                    open=float(row["Open"]),
                    high=float(row["High"]),
                    low=float(row["Low"]),
                    close=float(row["Close"]),
                    volume=float(row["Volume"]),
                    timestamp=dt,
                )
            )
        return bars

    async def fetch_latest_bar(
        self,
        symbol: str,
        timeframe: TimeFrame,
    ) -> Bar:
        interval = _YF_INTERVAL_MAP.get(timeframe, "1d")
        ticker = yf.Ticker(symbol)
        df = await asyncio.to_thread(
            ticker.history,
            interval=interval,
            period="1d",
        )

        if df.empty:
            raise ValueError(f"No data available for {symbol}")
        ts = df.index[-1]
        row = df.iloc[-1]
        dt = ts.to_pydatetime()
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return Bar(
            symbol=symbol,
            market=Market.US_STOCK,
            timeframe=timeframe,
            open=float(row["Open"]),
            high=float(row["High"]),
            low=float(row["Low"]),
            close=float(row["Close"]),
            volume=float(row["Volume"]),
            timestamp=dt,
        )
