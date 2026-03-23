from datetime import datetime, timezone

from collector.models.bar import Bar, Market, TimeFrame
from collector.models.tick import Tick


class TestBar:
    def test_create_bar(self) -> None:
        bar = Bar(
            symbol="AAPL",
            market=Market.US_STOCK,
            timeframe=TimeFrame.D1,
            open=150.0,
            high=155.0,
            low=149.0,
            close=153.0,
            volume=1_000_000.0,
            timestamp=datetime(2026, 1, 15, 16, 0, 0, tzinfo=timezone.utc),
        )
        assert bar.symbol == "AAPL"
        assert bar.market == Market.US_STOCK
        assert bar.timeframe == TimeFrame.D1
        assert bar.close == 153.0

    def test_bar_frozen(self) -> None:
        bar = Bar(
            symbol="600519",
            market=Market.A_STOCK,
            timeframe=TimeFrame.M1,
            open=1800.0,
            high=1810.0,
            low=1795.0,
            close=1805.0,
            volume=50000.0,
            timestamp=datetime(2026, 1, 15, 10, 30, 0, tzinfo=timezone.utc),
        )
        try:
            bar.close = 1900.0  # type: ignore[misc]
            assert False, "Should have raised"
        except Exception:
            pass

    def test_bar_serialization(self) -> None:
        bar = Bar(
            symbol="BTC/USDT",
            market=Market.CRYPTO,
            timeframe=TimeFrame.H1,
            open=42000.0,
            high=42500.0,
            low=41800.0,
            close=42300.0,
            volume=1234.5,
            timestamp=datetime(2026, 1, 15, 12, 0, 0, tzinfo=timezone.utc),
        )
        data = bar.model_dump()
        assert data["symbol"] == "BTC/USDT"
        assert data["market"] == "crypto"
        assert data["timeframe"] == "1h"

        json_str = bar.model_dump_json()
        restored = Bar.model_validate_json(json_str)
        assert restored == bar

    def test_all_timeframes(self) -> None:
        for tf in TimeFrame:
            bar = Bar(
                symbol="TEST",
                market=Market.A_STOCK,
                timeframe=tf,
                open=1.0,
                high=2.0,
                low=0.5,
                close=1.5,
                volume=100.0,
                timestamp=datetime(2026, 1, 1, tzinfo=timezone.utc),
            )
            assert bar.timeframe == tf


class TestTick:
    def test_create_tick(self) -> None:
        tick = Tick(
            symbol="ETH/USDT",
            market=Market.CRYPTO,
            price=2500.0,
            volume=10.5,
            bid=2499.5,
            ask=2500.5,
            timestamp=datetime(2026, 1, 15, 12, 0, 0, tzinfo=timezone.utc),
        )
        assert tick.symbol == "ETH/USDT"
        assert tick.price == 2500.0
        assert tick.bid == 2499.5

    def test_tick_frozen(self) -> None:
        tick = Tick(
            symbol="BTC/USDT",
            market=Market.CRYPTO,
            price=42000.0,
            volume=1.0,
            bid=41999.0,
            ask=42001.0,
            timestamp=datetime(2026, 1, 15, 12, 0, 0, tzinfo=timezone.utc),
        )
        try:
            tick.price = 50000.0  # type: ignore[misc]
            assert False, "Should have raised"
        except Exception:
            pass

    def test_tick_serialization(self) -> None:
        tick = Tick(
            symbol="000001",
            market=Market.A_STOCK,
            price=15.5,
            volume=10000.0,
            bid=15.49,
            ask=15.51,
            timestamp=datetime(2026, 1, 15, 10, 0, 0, tzinfo=timezone.utc),
        )
        json_str = tick.model_dump_json()
        restored = Tick.model_validate_json(json_str)
        assert restored == tick
        assert restored.market == Market.A_STOCK
