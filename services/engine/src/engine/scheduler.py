from __future__ import annotations

import asyncio
import logging
from collections.abc import Callable
from datetime import datetime, timezone

from croniter import croniter

logger = logging.getLogger(__name__)


class AsyncScheduler:
    """Lightweight asyncio cron scheduler using croniter."""

    def __init__(self) -> None:
        self._jobs: list[tuple[str, str, Callable]] = []  # (name, cron_expr, func)
        self._running = False
        self._tasks: list[asyncio.Task] = []

    def add_job(self, name: str, cron_expr: str, func: Callable) -> None:
        """Register a job with a cron expression."""
        if not croniter.is_valid(cron_expr):
            raise ValueError(f"Invalid cron expression: {cron_expr}")
        self._jobs.append((name, cron_expr, func))
        logger.info("Registered job '%s' with schedule '%s'", name, cron_expr)

    async def start(self) -> None:
        """Start all scheduled jobs."""
        self._running = True
        self._tasks = [
            asyncio.create_task(self._run_job(name, cron, func))
            for name, cron, func in self._jobs
        ]
        logger.info("Scheduler started with %d jobs", len(self._tasks))
        await asyncio.gather(*self._tasks, return_exceptions=True)

    async def _run_job(self, name: str, cron_expr: str, func: Callable) -> None:
        cron = croniter(cron_expr, datetime.now(timezone.utc))
        while self._running:
            next_time = cron.get_next(datetime)
            delay = (next_time - datetime.now(timezone.utc)).total_seconds()
            if delay > 0:
                try:
                    await asyncio.sleep(delay)
                except asyncio.CancelledError:
                    return
            if not self._running:
                return
            try:
                result = func()
                if asyncio.iscoroutine(result):
                    await result
                logger.debug("Job '%s' completed", name)
            except Exception:
                logger.exception("Job '%s' failed", name)

    def stop(self) -> None:
        """Stop all scheduled jobs."""
        self._running = False
        for task in self._tasks:
            task.cancel()
        self._tasks.clear()
        logger.info("Scheduler stopped")
