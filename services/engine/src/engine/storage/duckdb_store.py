from __future__ import annotations

import logging
from pathlib import Path

import duckdb
import pandas as pd

logger = logging.getLogger(__name__)

_DEFAULT_DB_PATH = Path(__file__).resolve().parents[5] / "data" / "kainex.duckdb"


class DuckDBStore:
    """Embedded DuckDB store for historical data analysis and backtest data."""

    def __init__(self, db_path: str | Path | None = None) -> None:
        self.db_path = Path(db_path) if db_path else _DEFAULT_DB_PATH
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = duckdb.connect(str(self.db_path))
        self._init_tables()

    def _init_tables(self) -> None:
        self._conn.execute("""
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

    def query_bars(
        self,
        symbol: str,
        market: str,
        timeframe: str,
        start: str | None = None,
        end: str | None = None,
    ) -> pd.DataFrame:
        """Query OHLCV bars, returning a DataFrame indexed by timestamp."""
        query = "SELECT * FROM bars WHERE symbol = ? AND market = ? AND timeframe = ?"
        params: list = [symbol, market, timeframe]
        if start:
            query += " AND ts >= ?"
            params.append(start)
        if end:
            query += " AND ts <= ?"
            params.append(end)
        query += " ORDER BY ts"
        df = self._conn.execute(query, params).fetchdf()
        if not df.empty:
            df = df.set_index("ts")
        return df

    def import_parquet(self, file_path: str | Path, table_name: str = "bars") -> int:
        """Import a Parquet file into the specified table. Returns row count."""
        file_path = Path(file_path)
        if not file_path.exists():
            raise FileNotFoundError(f"Parquet file not found: {file_path}")
        result = self._conn.execute(
            f"INSERT INTO {table_name} SELECT * FROM read_parquet(?)",
            [str(file_path)],
        )
        count = result.fetchone()[0] if result.description else 0
        logger.info("Imported %d rows from %s into %s", count, file_path, table_name)
        return count

    def export_parquet(self, query: str, file_path: str | Path) -> None:
        """Export a query result to a Parquet file."""
        file_path = Path(file_path)
        file_path.parent.mkdir(parents=True, exist_ok=True)
        self._conn.execute(
            f"COPY ({query}) TO ? (FORMAT PARQUET)",
            [str(file_path)],
        )
        logger.info("Exported query result to %s", file_path)

    def execute(
        self, query: str, params: list | None = None
    ) -> duckdb.DuckDBPyConnection:
        """Execute an arbitrary SQL query."""
        if params:
            return self._conn.execute(query, params)
        return self._conn.execute(query)

    def close(self) -> None:
        self._conn.close()
