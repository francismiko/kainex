from __future__ import annotations

import asyncio
import logging
from typing import TYPE_CHECKING

from collector.sources.onchain.blockchain_info import BlockchainInfoSource
from collector.sources.onchain.defillama import DefiLlamaSource
from collector.sources.onchain.fear_greed import FearGreedSource

if TYPE_CHECKING:
    from collector.storage.duckdb_writer import DuckDBWriter

logger = logging.getLogger(__name__)

# Global writer — set by main.py at startup
_writer: DuckDBWriter | None = None


def set_writer(writer: DuckDBWriter) -> None:
    global _writer
    _writer = writer


def _get_writer() -> DuckDBWriter:
    if _writer is None:
        raise RuntimeError("DuckDBWriter not initialized — call set_writer() first")
    return _writer


async def collect_onchain() -> None:
    """Collect on-chain metrics from all sources. Each source fails independently."""
    writer = _get_writer()

    sources = [
        ("defillama", DefiLlamaSource()),
        ("fear_greed", FearGreedSource()),
        ("blockchain_info", BlockchainInfoSource()),
    ]

    for name, source in sources:
        try:
            metrics = await source.fetch_metrics()
            if metrics:
                await asyncio.to_thread(writer.write_onchain_metrics, metrics)
                logger.info(
                    "On-chain metrics collected from %s: %d metrics", name, len(metrics)
                )
        except Exception:
            logger.warning("Failed to collect on-chain metrics from %s", name, exc_info=True)
