from __future__ import annotations

import logging
import os
import threading
from pathlib import Path

import duckdb

from collector.config import settings
from collector.models.bar import Bar
from collector.models.tick import Tick

logger = logging.getLogger(__name__)

INIT_SQL = """
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
);

CREATE TABLE IF NOT EXISTS ticks (
    symbol VARCHAR NOT NULL,
    market VARCHAR NOT NULL,
    price  DOUBLE NOT NULL,
    volume DOUBLE NOT NULL,
    bid    DOUBLE NOT NULL,
    ask    DOUBLE NOT NULL,
    ts     TIMESTAMP NOT NULL
);
"""


class DuckDBWriter:
    """Embedded DuckDB storage with Parquet export.

    DuckDB allows only a single write connection at a time, so all writes
    go through a single instance protected by a threading lock.
    """

    def __init__(self, db_path: str | None = None) -> None:
        self._db_path = db_path or settings.duckdb_path
        self._parquet_dir = settings.parquet_dir
        self._conn: duckdb.DuckDBPyConnection | None = None
        self._lock = threading.Lock()

    def connect(self) -> None:
        os.makedirs(os.path.dirname(self._db_path), exist_ok=True)
        self._conn = duckdb.connect(self._db_path)
        self._conn.execute(INIT_SQL)
        logger.info("DuckDB connected: %s", self._db_path)

    def close(self) -> None:
        if self._conn:
            self._conn.close()
            self._conn = None

    def write_bars(self, bars: list[Bar]) -> None:
        if not bars:
            return
        if self._conn is None:
            raise RuntimeError("DuckDBWriter not connected — call connect() first")
        records = [
            (
                b.symbol,
                b.market.value,
                b.timeframe.value,
                b.open,
                b.high,
                b.low,
                b.close,
                b.volume,
                b.timestamp,
            )
            for b in bars
        ]
        with self._lock:
            self._conn.executemany(
                """
                INSERT OR IGNORE INTO bars (symbol, market, timeframe, open, high, low, close, volume, ts)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                records,
            )

    def write_bar(self, bar: Bar) -> None:
        self.write_bars([bar])

    def write_tick(self, tick: Tick) -> None:
        if self._conn is None:
            raise RuntimeError("DuckDBWriter not connected — call connect() first")
        with self._lock:
            self._conn.execute(
                """
                INSERT INTO ticks (symbol, market, price, volume, bid, ask, ts)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    tick.symbol,
                    tick.market.value,
                    tick.price,
                    tick.volume,
                    tick.bid,
                    tick.ask,
                    tick.timestamp,
                ),
            )

    def query_bars(
        self,
        symbol: str,
        market: str,
        timeframe: str,
        limit: int = 500,
    ) -> list[dict]:
        if self._conn is None:
            raise RuntimeError("DuckDBWriter not connected — call connect() first")
        result = self._conn.execute(
            """
            SELECT symbol, market, timeframe, open, high, low, close, volume, ts
            FROM bars
            WHERE symbol = ? AND market = ? AND timeframe = ?
            ORDER BY ts DESC
            LIMIT ?
            """,
            (symbol, market, timeframe, limit),
        ).fetchall()
        columns = [
            "symbol",
            "market",
            "timeframe",
            "open",
            "high",
            "low",
            "close",
            "volume",
            "timestamp",
        ]
        return [dict(zip(columns, row)) for row in reversed(result)]

    def export_parquet(
        self, market: str | None = None, symbol: str | None = None
    ) -> None:
        """Export bars to Parquet files, partitioned by market/symbol."""
        if self._conn is None:
            raise RuntimeError("DuckDBWriter not connected — call connect() first")
        os.makedirs(self._parquet_dir, exist_ok=True)

        where_clauses: list[str] = []
        params: list[str] = []
        if market:
            where_clauses.append("market = ?")
            params.append(market)
        if symbol:
            where_clauses.append("symbol = ?")
            params.append(symbol)

        where = f"WHERE {' AND '.join(where_clauses)}" if where_clauses else ""

        # Get distinct market/symbol combos
        combos = self._conn.execute(
            f"SELECT DISTINCT market, symbol FROM bars {where}", params
        ).fetchall()

        for mkt, sym in combos:
            safe_sym = sym.replace("/", "_")
            out_dir = Path(self._parquet_dir) / mkt
            os.makedirs(out_dir, exist_ok=True)
            out_path = out_dir / f"{safe_sym}.parquet"
            self._conn.execute(
                f"""
                COPY (
                    SELECT * FROM bars
                    WHERE market = ? AND symbol = ?
                    ORDER BY ts
                ) TO '{out_path}' (FORMAT PARQUET)
                """,
                (mkt, sym),
            )
            logger.info("Exported parquet: %s", out_path)
