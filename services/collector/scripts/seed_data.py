"""Seed sample data into the shared DuckDB for development.

Usage:
    cd services/collector && uv run python scripts/seed_data.py
"""

from __future__ import annotations

import asyncio
import logging
import math
import random
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

# Ensure collector package is importable
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from collector.config import settings
from collector.models.bar import Bar, Market, TimeFrame
from collector.storage.duckdb_writer import DuckDBWriter

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)


def _generate_synthetic_bars(
    symbol: str,
    market: Market,
    days: int = 30,
    base_price: float = 100.0,
    volatility: float = 0.02,
) -> list[Bar]:
    """Generate realistic synthetic OHLCV bars for fallback."""
    bars: list[Bar] = []
    price = base_price
    now = datetime.now(timezone.utc)
    start = now - timedelta(days=days)

    for i in range(days):
        dt = start + timedelta(days=i)
        # Skip weekends for stock markets
        if market != Market.CRYPTO and dt.weekday() >= 5:
            continue

        change = random.gauss(0, volatility)
        open_ = price
        close = price * (1 + change)
        high = max(open_, close) * (1 + abs(random.gauss(0, volatility * 0.5)))
        low = min(open_, close) * (1 - abs(random.gauss(0, volatility * 0.5)))
        volume = random.uniform(1_000_000, 10_000_000)

        bars.append(Bar(
            symbol=symbol,
            market=market,
            timeframe=TimeFrame.D1,
            open=round(open_, 2),
            high=round(high, 2),
            low=round(low, 2),
            close=round(close, 2),
            volume=round(volume, 2),
            timestamp=dt.replace(hour=0, minute=0, second=0, microsecond=0),
        ))
        price = close

    return bars


async def _fetch_crypto_bars(symbol: str, days: int = 30) -> list[Bar]:
    """Fetch crypto bars via ccxt."""
    from collector.sources.crypto import CryptoSource

    source = CryptoSource()
    end = datetime.now(timezone.utc)
    start = end - timedelta(days=days)
    return await source.fetch_bars(symbol, TimeFrame.D1, start, end)


async def _fetch_us_stock_bars(symbol: str, days: int = 30) -> list[Bar]:
    """Fetch US stock bars via yfinance."""
    from collector.sources.us_stock import USStockSource

    source = USStockSource()
    end = datetime.now(timezone.utc)
    start = end - timedelta(days=days)
    return await source.fetch_bars(symbol, TimeFrame.D1, start, end)


async def _fetch_astock_bars(symbol: str, days: int = 30) -> list[Bar]:
    """Fetch A-stock bars via akshare."""
    from collector.sources.astock import AStockSource

    source = AStockSource()
    end = datetime.now(timezone.utc)
    start = end - timedelta(days=days)
    return await source.fetch_bars(symbol, TimeFrame.D1, start, end)


async def seed() -> None:
    writer = DuckDBWriter()
    writer.connect()

    tasks: list[dict] = [
        {
            "name": "BTC/USDT (crypto)",
            "fetch": lambda: _fetch_crypto_bars("BTC/USDT"),
            "fallback_args": {"symbol": "BTC/USDT", "market": Market.CRYPTO, "base_price": 85000.0, "volatility": 0.03},
        },
        {
            "name": "AAPL (US stock)",
            "fetch": lambda: _fetch_us_stock_bars("AAPL"),
            "fallback_args": {"symbol": "AAPL", "market": Market.US_STOCK, "base_price": 220.0, "volatility": 0.015},
        },
        {
            "name": "000001 (A-stock)",
            "fetch": lambda: _fetch_astock_bars("000001"),
            "fallback_args": {"symbol": "000001", "market": Market.A_STOCK, "base_price": 15.0, "volatility": 0.02},
        },
    ]

    all_bars: list[Bar] = []

    for task in tasks:
        logger.info("Fetching %s ...", task["name"])
        try:
            bars = await task["fetch"]()
            if bars:
                logger.info("  Got %d bars from data source", len(bars))
            else:
                raise ValueError("Empty result from data source")
        except Exception as e:
            logger.warning("  Data source failed (%s), generating synthetic data", e)
            bars = _generate_synthetic_bars(**task["fallback_args"])
            logger.info("  Generated %d synthetic bars", len(bars))
        all_bars.extend(bars)

    # Write all bars to DuckDB
    writer.write_bars(all_bars)
    logger.info("Wrote %d total bars to %s", len(all_bars), settings.duckdb_path)

    # Export to Parquet
    writer.export_parquet()
    logger.info("Exported Parquet files to %s", settings.parquet_dir)

    writer.close()
    logger.info("Seed complete!")


def main() -> None:
    asyncio.run(seed())


if __name__ == "__main__":
    main()
