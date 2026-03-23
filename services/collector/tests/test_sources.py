import pytest
from datetime import datetime, timezone
from unittest.mock import AsyncMock

from collector.models.bar import Bar, Market, TimeFrame
from collector.sources.base import AbstractDataSource, DataSourceManager


class FakeSource(AbstractDataSource):
    def __init__(self, market: Market, bars: list[Bar] | None = None, error: Exception | None = None):
        self._market = market
        self._bars = bars or []
        self._error = error

    @property
    def market(self) -> Market:
        return self._market

    async def fetch_bars(self, symbol, timeframe, start, end):
        if self._error:
            raise self._error
        return self._bars

    async def fetch_latest_bar(self, symbol, timeframe):
        if self._error:
            raise self._error
        if not self._bars:
            raise ValueError("No data")
        return self._bars[-1]


def _make_bar(symbol: str = "TEST") -> Bar:
    return Bar(
        symbol=symbol,
        market=Market.US_STOCK,
        timeframe=TimeFrame.D1,
        open=100.0,
        high=105.0,
        low=99.0,
        close=103.0,
        volume=5000.0,
        timestamp=datetime(2026, 1, 15, tzinfo=timezone.utc),
    )


class TestDataSourceManager:
    @pytest.mark.asyncio
    async def test_first_source_succeeds(self) -> None:
        bar = _make_bar()
        source1 = FakeSource(Market.US_STOCK, bars=[bar])
        source2 = FakeSource(Market.US_STOCK, error=RuntimeError("should not be called"))

        mgr = DataSourceManager([source1, source2])
        result = await mgr.fetch_latest_bar("TEST", TimeFrame.D1)
        assert result == bar

    @pytest.mark.asyncio
    async def test_fallback_on_failure(self) -> None:
        bar = _make_bar()
        source1 = FakeSource(Market.US_STOCK, error=RuntimeError("source1 down"))
        source2 = FakeSource(Market.US_STOCK, bars=[bar])

        mgr = DataSourceManager([source1, source2])
        result = await mgr.fetch_latest_bar("TEST", TimeFrame.D1)
        assert result == bar

    @pytest.mark.asyncio
    async def test_all_sources_fail(self) -> None:
        source1 = FakeSource(Market.US_STOCK, error=RuntimeError("fail1"))
        source2 = FakeSource(Market.US_STOCK, error=RuntimeError("fail2"))

        mgr = DataSourceManager([source1, source2])
        with pytest.raises(RuntimeError, match="All data sources failed"):
            await mgr.fetch_latest_bar("TEST", TimeFrame.D1)

    @pytest.mark.asyncio
    async def test_fetch_bars_fallback(self) -> None:
        bar = _make_bar()
        source1 = FakeSource(Market.US_STOCK, error=RuntimeError("fail"))
        source2 = FakeSource(Market.US_STOCK, bars=[bar])

        mgr = DataSourceManager([source1, source2])
        now = datetime.now(timezone.utc)
        result = await mgr.fetch_bars("TEST", TimeFrame.D1, now, now)
        assert result == [bar]
