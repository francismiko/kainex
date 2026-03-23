from __future__ import annotations

import logging
from datetime import datetime, timezone

import httpx

from collector.models.onchain import OnChainMetric

logger = logging.getLogger(__name__)

CHARTS_BASE = "https://api.blockchain.info/charts"


class BlockchainInfoSource:
    """Fetch BTC on-chain metrics from Blockchain.info."""

    async def fetch_metrics(self) -> list[OnChainMetric]:
        metrics: list[OnChainMetric] = []
        now = datetime.now(timezone.utc)

        async with httpx.AsyncClient(timeout=30) as client:
            # Active addresses
            active = await self._fetch_chart(
                client, "n-unique-addresses", "30days"
            )
            if active is not None:
                metrics.append(
                    OnChainMetric(
                        metric_name="btc_active_addresses",
                        asset="BTC",
                        value=active,
                        source="blockchain_info",
                        timestamp=now,
                    )
                )

            # Transaction count
            tx_count = await self._fetch_chart(
                client, "n-transactions", "30days"
            )
            if tx_count is not None:
                metrics.append(
                    OnChainMetric(
                        metric_name="btc_transaction_count",
                        asset="BTC",
                        value=tx_count,
                        source="blockchain_info",
                        timestamp=now,
                    )
                )

            # Hash rate
            hashrate = await self._fetch_chart(client, "hash-rate", "30days")
            if hashrate is not None:
                metrics.append(
                    OnChainMetric(
                        metric_name="btc_hash_rate",
                        asset="BTC",
                        value=hashrate,
                        source="blockchain_info",
                        timestamp=now,
                    )
                )

        return metrics

    async def _fetch_chart(
        self,
        client: httpx.AsyncClient,
        chart_name: str,
        timespan: str,
    ) -> float | None:
        """Fetch latest value from a blockchain.info chart endpoint."""
        try:
            resp = await client.get(
                f"{CHARTS_BASE}/{chart_name}",
                params={"timespan": timespan, "format": "json"},
            )
            resp.raise_for_status()
            data = resp.json()
            values = data.get("values", [])
            if values:
                return float(values[-1]["y"])
        except Exception:
            logger.warning("Failed to fetch %s from blockchain.info", chart_name)
        return None
