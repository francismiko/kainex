from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone

import baostock as bs

from collector.models.bar import Bar, Market, TimeFrame

from .base import AbstractDataSource

logger = logging.getLogger(__name__)

# BaoStock supports 5/15/30/60 min and daily, NOT 1-min
_FREQUENCY_MAP = {
    TimeFrame.M5: "5",
    TimeFrame.M15: "15",
    TimeFrame.H1: "60",
    TimeFrame.D1: "d",
    TimeFrame.W1: "w",
}


def _to_baostock_code(symbol: str) -> str:
    """Convert plain symbol like '000001' to baostock format 'sz.000001'."""
    if symbol.startswith(("sh.", "sz.")):
        return symbol
    if symbol.startswith("6"):
        return f"sh.{symbol}"
    return f"sz.{symbol}"


class BaoStockSource(AbstractDataSource):
    """BaoStock A-stock data source (fallback for AKShare)."""

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
        frequency = _FREQUENCY_MAP.get(timeframe)
        if frequency is None:
            raise ValueError(
                f"BaoStock does not support {timeframe.value} timeframe"
            )

        code = _to_baostock_code(symbol)
        start_str = start.strftime("%Y-%m-%d")
        end_str = end.strftime("%Y-%m-%d")

        def _query() -> list[list[str]]:
            lg = bs.login()
            if lg.error_code != "0":
                raise RuntimeError(f"BaoStock login failed: {lg.error_msg}")
            try:
                fields = "date,time,open,high,low,close,volume"
                if frequency in ("d", "w"):
                    fields = "date,open,high,low,close,volume"

                rs = bs.query_history_k_data_plus(
                    code,
                    fields,
                    start_date=start_str,
                    end_date=end_str,
                    frequency=frequency,
                    adjustflag="3",  # no adjustment
                )
                if rs.error_code != "0":
                    raise RuntimeError(f"BaoStock query failed: {rs.error_msg}")

                rows: list[list[str]] = []
                while rs.next():
                    rows.append(rs.get_row_data())
                return rows
            finally:
                bs.logout()

        rows = await asyncio.to_thread(_query)

        bars: list[Bar] = []
        is_daily = frequency in ("d", "w")
        for row in rows:
            if is_daily:
                date_str, open_, high, low, close, volume = row
                ts = datetime.strptime(date_str, "%Y-%m-%d").replace(tzinfo=timezone.utc)
            else:
                date_str, time_str, open_, high, low, close, volume = row
                # time_str format: "20260115093500000"
                ts_str = f"{date_str} {time_str[:8]}"
                ts = datetime.strptime(ts_str, "%Y%m%d %H%M%S%f").replace(tzinfo=timezone.utc)

            if not open_ or not close:
                continue

            bars.append(
                Bar(
                    symbol=symbol,
                    market=Market.A_STOCK,
                    timeframe=timeframe,
                    open=float(open_),
                    high=float(high),
                    low=float(low),
                    close=float(close),
                    volume=float(volume),
                    timestamp=ts,
                )
            )
        return bars

    async def fetch_latest_bar(
        self,
        symbol: str,
        timeframe: TimeFrame,
    ) -> Bar:
        end = datetime.now(timezone.utc)
        start = end.replace(hour=0, minute=0, second=0, microsecond=0)
        bars = await self.fetch_bars(symbol, timeframe, start, end)
        if not bars:
            raise ValueError(f"No BaoStock data available for {symbol}")
        return bars[-1]
