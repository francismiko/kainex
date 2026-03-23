from __future__ import annotations

import asyncio
import logging
from typing import TYPE_CHECKING

from collector.config import settings
from collector.models.bar import TimeFrame
from collector.sources.base import DataSourceManager

if TYPE_CHECKING:
    from collector.storage.duckdb_writer import DuckDBWriter

logger = logging.getLogger(__name__)

# Global writer — set by main.py at startup
_writer: DuckDBWriter | None = None


def set_writer(writer: DuckDBWriter) -> None:
    global _writer
    _writer = writer


def _get_writer() -> DuckDBWriter:
    assert _writer is not None, "DuckDBWriter not initialized — call set_writer() first"
    return _writer


def build_astock_manager() -> DataSourceManager:
    from collector.sources.astock import AStockSource
    from collector.sources.baostock_source import BaoStockSource

    source_map = {
        "akshare": AStockSource,
        "baostock": BaoStockSource,
    }
    sources = []
    for name in settings.astock_sources:
        cls = source_map.get(name)
        if cls:
            sources.append(cls())
    return DataSourceManager(sources)


def build_us_stock_manager() -> DataSourceManager:
    from collector.sources.finnhub_source import FinnhubSource
    from collector.sources.us_stock import USStockSource

    source_map = {
        "finnhub": lambda: FinnhubSource(),
        "yfinance": lambda: USStockSource(),
    }
    sources = []
    for name in settings.us_stock_sources:
        factory = source_map.get(name)
        if factory:
            sources.append(factory())
    return DataSourceManager(sources)


def build_crypto_manager() -> DataSourceManager:
    from collector.sources.crypto import CryptoSource

    source_map = {
        "ccxt": lambda: CryptoSource(),
    }
    sources = []
    for name in settings.crypto_sources:
        factory = source_map.get(name)
        if factory:
            sources.append(factory())
    return DataSourceManager(sources)


async def collect_astock_intraday() -> None:
    manager = build_astock_manager()
    writer = _get_writer()

    for symbol in settings.astock_symbols:
        try:
            bar = await manager.fetch_latest_bar(symbol, TimeFrame.M1)
            await asyncio.to_thread(writer.write_bar, bar)
            logger.info("A-stock bar collected: %s", bar.symbol)
        except Exception:
            logger.exception("Failed to collect A-stock %s", symbol)


async def collect_us_stock_intraday() -> None:
    manager = build_us_stock_manager()
    writer = _get_writer()

    for symbol in settings.us_stock_symbols:
        try:
            bar = await manager.fetch_latest_bar(symbol, TimeFrame.M5)
            await asyncio.to_thread(writer.write_bar, bar)
            logger.info("US-stock bar collected: %s", bar.symbol)
        except Exception:
            logger.exception("Failed to collect US-stock %s", symbol)


async def collect_crypto() -> None:
    manager = build_crypto_manager()
    writer = _get_writer()

    for symbol in settings.crypto_symbols:
        try:
            bar = await manager.fetch_latest_bar(symbol, TimeFrame.M1)
            await asyncio.to_thread(writer.write_bar, bar)
            logger.info("Crypto bar collected: %s", bar.symbol)
        except Exception:
            logger.exception("Failed to collect crypto %s", symbol)
