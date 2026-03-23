import os
import tempfile
from datetime import datetime, timezone

from collector.models.bar import Bar, Market, TimeFrame
from collector.models.tick import Tick
from collector.storage.duckdb_writer import DuckDBWriter


class TestDuckDBWriter:
    def _make_writer(self, tmp_dir: str) -> DuckDBWriter:
        db_path = os.path.join(tmp_dir, "test.duckdb")
        writer = DuckDBWriter(db_path=db_path)
        writer._parquet_dir = os.path.join(tmp_dir, "parquet")
        writer.connect()
        return writer

    def _make_bar(self, symbol: str = "AAPL", **kwargs) -> Bar:
        defaults = dict(
            symbol=symbol,
            market=Market.US_STOCK,
            timeframe=TimeFrame.D1,
            open=150.0,
            high=155.0,
            low=149.0,
            close=153.0,
            volume=1_000_000.0,
            timestamp=datetime(2026, 1, 15, 16, 0, 0, tzinfo=timezone.utc),
        )
        defaults.update(kwargs)
        return Bar(**defaults)

    def test_write_and_query_bar(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            writer = self._make_writer(tmp)
            try:
                bar = self._make_bar()
                writer.write_bar(bar)

                results = writer.query_bars("AAPL", "us_stock", "1d")
                assert len(results) == 1
                assert results[0]["symbol"] == "AAPL"
                assert results[0]["close"] == 153.0
            finally:
                writer.close()

    def test_write_bars_batch(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            writer = self._make_writer(tmp)
            try:
                bars = [
                    self._make_bar(
                        timestamp=datetime(2026, 1, i, 16, 0, 0, tzinfo=timezone.utc),
                        close=150.0 + i,
                    )
                    for i in range(1, 6)
                ]
                writer.write_bars(bars)

                results = writer.query_bars("AAPL", "us_stock", "1d")
                assert len(results) == 5
            finally:
                writer.close()

    def test_write_duplicate_ignored(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            writer = self._make_writer(tmp)
            try:
                bar = self._make_bar()
                writer.write_bar(bar)
                writer.write_bar(bar)  # duplicate

                results = writer.query_bars("AAPL", "us_stock", "1d")
                assert len(results) == 1
            finally:
                writer.close()

    def test_write_tick(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            writer = self._make_writer(tmp)
            try:
                tick = Tick(
                    symbol="BTC/USDT",
                    market=Market.CRYPTO,
                    price=42000.0,
                    volume=1.5,
                    bid=41999.0,
                    ask=42001.0,
                    timestamp=datetime(2026, 1, 15, 12, 0, 0, tzinfo=timezone.utc),
                )
                writer.write_tick(tick)

                assert writer._conn is not None
                result = writer._conn.execute("SELECT count(*) FROM ticks").fetchone()
                assert result[0] == 1
            finally:
                writer.close()

    def test_export_parquet(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            writer = self._make_writer(tmp)
            try:
                bar = self._make_bar()
                writer.write_bar(bar)
                writer.export_parquet()

                parquet_path = os.path.join(tmp, "parquet", "us_stock", "AAPL.parquet")
                assert os.path.exists(parquet_path)
            finally:
                writer.close()
