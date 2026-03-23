from __future__ import annotations

import asyncio
import logging
import os
import time

from croniter import croniter

from collector.config import settings
from collector.jobs import eod as eod_mod
from collector.jobs import intraday as intraday_mod
from collector.jobs.eod import aggregate_eod
from collector.jobs.intraday import (
    collect_astock_intraday,
    collect_crypto,
    collect_us_stock_intraday,
)
from collector.storage.duckdb_writer import DuckDBWriter

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


class CollectorScheduler:
    """Lightweight asyncio scheduler using croniter."""

    def __init__(self, writer: DuckDBWriter) -> None:
        self._writer = writer

    async def run(self) -> None:
        s = settings
        astock_cron = (
            f"*/{s.astock_interval_minutes} "
            f"{s.astock_cron_start_hour}-{s.astock_cron_end_hour} "
            f"* * 1-5"
        )
        us_stock_cron = (
            f"*/{s.us_stock_interval_minutes} "
            f"{s.us_stock_cron_start_hour}-{s.us_stock_cron_end_hour} "
            f"* * 1-5"
        )

        await asyncio.gather(
            self._schedule_cron("astock", astock_cron, collect_astock_intraday),
            self._schedule_cron("us_stock", us_stock_cron, collect_us_stock_intraday),
            self._schedule_interval("crypto", s.crypto_interval_minutes * 60, collect_crypto),
            self._schedule_cron("eod", "0 23 * * *", aggregate_eod),
        )

    async def _schedule_cron(self, name: str, expr: str, func) -> None:
        cron = croniter(expr)
        logger.info("Scheduled cron job [%s]: %s", name, expr)
        while True:
            next_ts = cron.get_next(float)
            delay = max(0, next_ts - time.time())
            await asyncio.sleep(delay)
            try:
                await func()
            except Exception:
                logger.exception("Job [%s] failed", name)

    async def _schedule_interval(self, name: str, seconds: int, func) -> None:
        logger.info("Scheduled interval job [%s]: every %ds", name, seconds)
        while True:
            try:
                await func()
            except Exception:
                logger.exception("Job [%s] failed", name)
            await asyncio.sleep(seconds)


async def run() -> None:
    # Ensure data directory exists
    os.makedirs(settings.data_dir, exist_ok=True)

    # Initialize shared DuckDB writer
    writer = DuckDBWriter()
    writer.connect()

    # Inject writer into job modules
    intraday_mod.set_writer(writer)
    eod_mod.set_writer(writer)

    try:
        scheduler = CollectorScheduler(writer)
        logger.info("Collector scheduler started")
        await scheduler.run()
    finally:
        writer.close()


def main() -> None:
    try:
        asyncio.run(run())
    except KeyboardInterrupt:
        logger.info("Collector stopped")


if __name__ == "__main__":
    main()
