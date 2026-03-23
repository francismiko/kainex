import asyncio
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

import akshare as ak

from collector.models.bar import Bar, Market, TimeFrame

from .base import AbstractDataSource


class AStockSource(AbstractDataSource):
    @property
    def market(self) -> Market:
        return Market.A_STOCK

    async def fetch_bars(
        self,
        symbol: str,
        timeframe: TimeFrame,
        start: datetime,
        end: datetime,
    ) -> list[Bar]:
        period_map = {
            TimeFrame.M1: "1",
            TimeFrame.M5: "5",
            TimeFrame.M15: "15",
            TimeFrame.H1: "60",
            TimeFrame.D1: "daily",
        }
        period = period_map.get(timeframe, "daily")

        df = await asyncio.to_thread(
            ak.stock_zh_a_hist_min_em,
            symbol=symbol,
            period=period,
            start_date=start.strftime("%Y-%m-%d %H:%M:%S"),
            end_date=end.strftime("%Y-%m-%d %H:%M:%S"),
        )

        bars: list[Bar] = []
        for _, row in df.iterrows():
            ts = datetime.fromisoformat(str(row["时间"]))
            if ts.tzinfo is None:
                ts = ts.replace(tzinfo=ZoneInfo("Asia/Shanghai")).astimezone(timezone.utc)
            bars.append(
                Bar(
                    symbol=symbol,
                    market=Market.A_STOCK,
                    timeframe=timeframe,
                    open=float(row["开盘"]),
                    high=float(row["最高"]),
                    low=float(row["最低"]),
                    close=float(row["收盘"]),
                    volume=float(row["成交量"]),
                    timestamp=ts,
                )
            )
        return bars

    async def fetch_latest_bar(
        self,
        symbol: str,
        timeframe: TimeFrame,
    ) -> Bar:
        now = datetime.now(timezone.utc)
        bars = await self.fetch_bars(
            symbol,
            timeframe,
            start=now.replace(hour=0, minute=0, second=0),
            end=now,
        )
        if not bars:
            raise ValueError(f"No data available for {symbol}")
        return bars[-1]
