import tempfile
from pathlib import Path

import duckdb
import numpy as np
import pandas as pd
import pytest

from agent.market_analyzer import MarketAnalyzer, _compute_rsi, _safe_float


@pytest.fixture()
def duckdb_file(tmp_path: Path) -> str:
    """Create a temporary DuckDB with sample bar data."""
    db_path = tmp_path / "test.duckdb"
    conn = duckdb.connect(str(db_path))
    conn.execute("""
        CREATE TABLE bars (
            symbol    VARCHAR NOT NULL,
            market    VARCHAR NOT NULL,
            timeframe VARCHAR NOT NULL,
            open      DOUBLE NOT NULL,
            high      DOUBLE NOT NULL,
            low       DOUBLE NOT NULL,
            close     DOUBLE NOT NULL,
            volume    DOUBLE NOT NULL,
            ts        TIMESTAMP NOT NULL,
            UNIQUE(symbol, market, timeframe, ts)
        )
    """)

    # Insert 50 bars of synthetic data
    np.random.seed(42)
    base_price = 60000.0
    dates = pd.date_range("2024-01-01", periods=50, freq="D")
    for i, dt in enumerate(dates):
        noise = np.random.normal(0, 500)
        close = base_price + i * 100 + noise
        high = close + abs(np.random.normal(0, 200))
        low = close - abs(np.random.normal(0, 200))
        open_ = close + np.random.normal(0, 100)
        volume = np.random.uniform(1000, 5000)
        conn.execute(
            "INSERT INTO bars VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            ["BTC/USDT", "crypto", "1d", open_, high, low, close, volume, dt],
        )

    conn.close()
    return str(db_path)


class TestMarketAnalyzer:
    @pytest.mark.asyncio
    async def test_get_market_summary_with_data(self, duckdb_file: str):
        analyzer = MarketAnalyzer(duckdb_path=duckdb_file, engine_api_url="http://localhost:9999")
        summary = await analyzer.get_market_summary("BTC/USDT")
        await analyzer.close()

        assert summary["available"] is True
        assert summary["bars"] == 50
        assert summary["symbol"] == "BTC/USDT"
        assert summary["last_price"] > 0
        assert summary["sma_20"] is not None
        assert summary["rsi_14"] is not None

    @pytest.mark.asyncio
    async def test_get_market_summary_no_data(self, duckdb_file: str):
        analyzer = MarketAnalyzer(duckdb_path=duckdb_file, engine_api_url="http://localhost:9999")
        summary = await analyzer.get_market_summary("NONEXISTENT/PAIR")
        await analyzer.close()

        assert summary["available"] is False
        assert summary["bars"] == 0

    @pytest.mark.asyncio
    async def test_portfolio_state_fallback(self, duckdb_file: str):
        """Portfolio fetch should fall back gracefully when the engine is unreachable."""
        analyzer = MarketAnalyzer(duckdb_path=duckdb_file, engine_api_url="http://localhost:9999")
        portfolio = await analyzer.get_portfolio_state()
        await analyzer.close()

        assert portfolio["total_value"] == 0.0
        assert portfolio["positions"] == []


class TestComputeRsi:
    def test_rsi_range(self):
        np.random.seed(0)
        prices = pd.Series(np.cumsum(np.random.randn(100)) + 100)
        rsi = _compute_rsi(prices, 14)
        valid = rsi.dropna()
        assert len(valid) > 0
        assert (valid >= 0).all()
        assert (valid <= 100).all()

    def test_rsi_monotonic_up(self):
        prices = pd.Series(range(1, 50), dtype=float)
        rsi = _compute_rsi(prices, 14)
        # All gains, RSI should be very high
        assert rsi.iloc[-1] > 90

    def test_rsi_monotonic_down(self):
        prices = pd.Series(range(50, 1, -1), dtype=float)
        rsi = _compute_rsi(prices, 14)
        # All losses, RSI should be very low
        assert rsi.iloc[-1] < 10


class TestSafeFloat:
    def test_normal_float(self):
        assert _safe_float(1.5) == 1.5

    def test_nan(self):
        assert _safe_float(float("nan")) is None

    def test_nan_with_default(self):
        assert _safe_float(float("nan"), 0.0) == 0.0

    def test_none_input(self):
        assert _safe_float(None) is None

    def test_string_input(self):
        assert _safe_float("abc") is None
