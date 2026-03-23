"""End-to-end integration tests for Collector -> Engine data pipeline."""

from __future__ import annotations

import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path

import duckdb
import numpy as np
import pandas as pd
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from engine.core.backtest import BacktestEngine
from engine.indicators.technical import TechnicalIndicators
from engine.storage.duckdb_store import DuckDBStore
from engine.storage.sqlite_store import SQLiteStore
from engine.strategies.examples.sma_crossover import SmaCrossoverLegacy
from engine.strategies.registry import registry as strategy_registry


def _seed_bars_into_duckdb(db_path: Path, n_days: int = 60) -> None:
    """Write synthetic bar data directly into a DuckDB file, mimicking Collector output."""
    conn = duckdb.connect(str(db_path))
    conn.execute("""
        CREATE TABLE IF NOT EXISTS bars (
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

    rng = np.random.RandomState(42)
    now = datetime.now(timezone.utc)
    start = now - timedelta(days=n_days)

    datasets = [
        ("BTC/USDT", "crypto", 85000.0, 0.03),
        ("AAPL", "us_stock", 220.0, 0.015),
        ("000001", "a_stock", 15.0, 0.02),
    ]

    for symbol, market, base_price, vol in datasets:
        price = base_price
        for i in range(n_days):
            dt = start + timedelta(days=i)
            # Skip weekends for stocks
            if market != "crypto" and dt.weekday() >= 5:
                continue
            change = rng.normal(0, vol)
            open_ = price
            close = price * (1 + change)
            high = max(open_, close) * (1 + abs(rng.normal(0, vol * 0.5)))
            low = min(open_, close) * (1 - abs(rng.normal(0, vol * 0.5)))
            volume = rng.uniform(1_000_000, 10_000_000)

            conn.execute(
                "INSERT OR IGNORE INTO bars VALUES (?, ?, '1d', ?, ?, ?, ?, ?, ?)",
                (symbol, market, round(open_, 2), round(high, 2), round(low, 2),
                 round(close, 2), round(volume, 2),
                 dt.replace(hour=0, minute=0, second=0, microsecond=0)),
            )
            price = close

    conn.close()


# -- Test 1: Seed data -> DuckDB query -> confirm data exists --

class TestSeedDataQuery:
    def test_seed_and_query(self, tmp_path):
        db_path = tmp_path / "test.duckdb"
        _seed_bars_into_duckdb(db_path)

        store = DuckDBStore(db_path=db_path)
        try:
            # Crypto should have ~60 rows (every day)
            df_crypto = store.query_bars("BTC/USDT", "crypto", "1d")
            assert not df_crypto.empty
            assert len(df_crypto) >= 50

            # US stock should have ~42 rows (weekdays only)
            df_us = store.query_bars("AAPL", "us_stock", "1d")
            assert not df_us.empty
            assert len(df_us) >= 30

            # A-stock should have ~42 rows (weekdays only)
            df_a = store.query_bars("000001", "a_stock", "1d")
            assert not df_a.empty
            assert len(df_a) >= 30

            # Check column structure
            for df in [df_crypto, df_us, df_a]:
                assert "open" in df.columns
                assert "close" in df.columns
                assert "volume" in df.columns
        finally:
            store.close()


# -- Test 2: DuckDB has data -> BacktestEngine.run() -> valid results --

class TestBacktestWithSeededData:
    def test_backtest_returns_valid_result(self, tmp_path):
        db_path = tmp_path / "test.duckdb"
        _seed_bars_into_duckdb(db_path, n_days=120)

        store = DuckDBStore(db_path=db_path)
        try:
            df = store.query_bars("BTC/USDT", "crypto", "1d")
            assert not df.empty

            # Add SMA indicators
            df["sma_short"] = TechnicalIndicators.sma(df["close"], length=10)
            df["sma_long"] = TechnicalIndicators.sma(df["close"], length=30)
            df["symbol"] = "BTC/USDT"

            strategy = SmaCrossoverLegacy(short_window=10, long_window=30)
            engine = BacktestEngine(initial_capital=100_000.0)
            result = engine.run(strategy, df)

            assert result.equity_curve is not None
            assert len(result.equity_curve) == len(df)
            assert "sharpe_ratio" in result.metrics
            assert "max_drawdown" in result.metrics
            assert "total_return" in result.metrics
            # Equity should start at initial capital
            assert abs(result.equity_curve.iloc[0] - 100_000.0) < 1.0
        finally:
            store.close()


# -- Test 3: FastAPI /api/backtest/run -> BacktestResponse --

async def _make_test_app(duckdb_store: DuckDBStore, sqlite_store: SQLiteStore) -> FastAPI:
    """Create a test FastAPI app with stores injected directly (no lifespan)."""
    from engine.api.routes import backtest, market_data, portfolio, strategies

    await sqlite_store.connect()

    test_app = FastAPI()
    test_app.state.sqlite_store = sqlite_store
    test_app.state.duckdb_store = duckdb_store
    test_app.state.strategy_registry = strategy_registry

    test_app.include_router(backtest.router, prefix="/api/backtest", tags=["backtest"])
    test_app.include_router(market_data.router, prefix="/api/market-data", tags=["market-data"])
    test_app.include_router(portfolio.router, prefix="/api/portfolio", tags=["portfolio"])
    test_app.include_router(strategies.router, prefix="/api/strategies", tags=["strategies"])
    return test_app


class TestApiBacktestIntegration:
    @pytest.mark.asyncio
    async def test_backtest_api_endpoint(self, tmp_path):
        import httpx
        db_path = tmp_path / "test.duckdb"
        sqlite_path = tmp_path / "test_state.db"
        _seed_bars_into_duckdb(db_path, n_days=120)

        duckdb_store = DuckDBStore(db_path=db_path)
        sqlite_store = SQLiteStore(db_path=sqlite_path)
        test_app = await _make_test_app(duckdb_store, sqlite_store)

        transport = httpx.ASGITransport(app=test_app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            now = datetime.now(timezone.utc)
            resp = await client.post("/api/backtest/run", json={
                "strategy_id": "sma_crossover",
                "start_date": (now - timedelta(days=100)).isoformat(),
                "end_date": now.isoformat(),
                "initial_capital": 100000.0,
                "market": "crypto",
                "symbols": ["BTC/USDT"],
            })
            assert resp.status_code == 200
            data = resp.json()
            assert data["strategy_id"] == "sma_crossover"
            assert data["status"] == "completed"
            assert "metrics" in data
            assert isinstance(data["equity_curve"], list)
        await sqlite_store.close()
        duckdb_store.close()


# -- Test 4: FastAPI /api/market-data/bars -> returns data --

class TestApiMarketDataIntegration:
    @pytest.mark.asyncio
    async def test_market_data_bars(self, tmp_path):
        import httpx
        db_path = tmp_path / "test.duckdb"
        sqlite_path = tmp_path / "test_state.db"
        _seed_bars_into_duckdb(db_path)

        duckdb_store = DuckDBStore(db_path=db_path)
        sqlite_store = SQLiteStore(db_path=sqlite_path)
        test_app = await _make_test_app(duckdb_store, sqlite_store)

        transport = httpx.ASGITransport(app=test_app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.get("/api/market-data/bars?symbol=BTC/USDT&market=crypto&timeframe=1d")
            assert resp.status_code == 200
            data = resp.json()
            assert isinstance(data, list)
            assert len(data) > 0
            bar = data[0]
            assert bar["symbol"] == "BTC/USDT"
            assert bar["market"] == "crypto"
            assert "open" in bar
            assert "close" in bar
            assert "volume" in bar

            # Test with US stock
            resp_us = await client.get("/api/market-data/bars?symbol=AAPL&market=us_stock&timeframe=1d")
            assert resp_us.status_code == 200
            data_us = resp_us.json()
            assert len(data_us) > 0
        await sqlite_store.close()
        duckdb_store.close()
