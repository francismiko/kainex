from __future__ import annotations

import asyncio
import logging
from datetime import date
from typing import TYPE_CHECKING

import exchange_calendars as xcals

from collector.config import settings
from collector.models.bar import TimeFrame
from collector.sources.base import DataSourceManager

if TYPE_CHECKING:
    from collector.storage.duckdb_writer import DuckDBWriter

logger = logging.getLogger(__name__)

_xshg_calendar = xcals.get_calendar("XSHG")

# Global writer — set by main.py at startup
_writer: DuckDBWriter | None = None


def set_writer(writer: DuckDBWriter) -> None:
    global _writer
    _writer = writer


def _get_writer() -> DuckDBWriter:
    if _writer is None:
        raise RuntimeError("DuckDBWriter not initialized — call set_writer() first")
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
    today = date.today()
    if not _xshg_calendar.is_session(today):
        logger.info("Skipping A-stock collection: %s is not a XSHG trading day", today)
        return

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


async def collect_funding_rates() -> None:
    """Collect funding rates for crypto perpetual contracts (every 8h)."""
    from collector.sources.funding_rate import FundingRateSource

    source = FundingRateSource()
    writer = _get_writer()

    # Use the same crypto symbols but with perpetual suffixes if needed
    symbols = settings.crypto_symbols
    try:
        rates = await source.fetch_funding_rates(symbols)
        if rates:
            await asyncio.to_thread(writer.write_funding_rates, rates)
            logger.info("Funding rates collected for %d symbols", len(rates))
    except Exception:
        logger.exception("Failed to collect funding rates")
