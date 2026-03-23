from __future__ import annotations

import asyncio
import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collector.storage.duckdb_writer import DuckDBWriter

logger = logging.getLogger(__name__)

# Global writer — shared with intraday jobs
_writer: DuckDBWriter | None = None


def set_writer(writer: DuckDBWriter) -> None:
    global _writer
    _writer = writer


def _get_writer() -> DuckDBWriter:
    assert _writer is not None, "DuckDBWriter not initialized — call set_writer() first"
    return _writer


def _aggregate(writer: DuckDBWriter) -> None:
    assert writer._conn is not None
    writer._conn.execute(
        """
        INSERT OR REPLACE INTO bars (symbol, market, timeframe, open, high, low, close, volume, ts)
        SELECT
            symbol,
            market,
            '1d' AS timeframe,
            -- First open of the day
            first(open ORDER BY ts),
            max(high),
            min(low),
            -- Last close of the day
            last(close ORDER BY ts),
            sum(volume),
            date_trunc('day', ts)
        FROM bars
        WHERE timeframe IN ('1m', '5m', '15m', '1h')
          AND ts::DATE = current_date
        GROUP BY symbol, market, date_trunc('day', ts)
        """
    )
    # Export updated data to Parquet
    writer.export_parquet()
    logger.info("EOD aggregation completed")


async def aggregate_eod() -> None:
    """End-of-day aggregation: compute daily OHLCV from intraday bars, export Parquet."""
    writer = _get_writer()
    await asyncio.to_thread(_aggregate, writer)
