from __future__ import annotations

import logging
from datetime import datetime, timezone

import httpx

from collector.models.onchain import OnChainMetric

logger = logging.getLogger(__name__)

STABLECOINS_URL = "https://stablecoins.llama.fi/stablecoins"
STABLECOIN_CHARTS_URL = "https://stablecoins.llama.fi/stablecoincharts/all"


class DefiLlamaSource:
    """Fetch stablecoin supply data from DefiLlama."""

    async def fetch_metrics(self) -> list[OnChainMetric]:
        metrics: list[OnChainMetric] = []
        now = datetime.now(timezone.utc)

        async with httpx.AsyncClient(timeout=30) as client:
            # Current stablecoin supply
            resp = await client.get(STABLECOINS_URL)
            resp.raise_for_status()
            data = resp.json()

            total_supply = 0.0
            for coin in data.get("peggedAssets", []):
                chain_circ = coin.get("chainCirculating", {})
                for chain_data in chain_circ.values():
                    current = chain_data.get("current", {})
                    total_supply += current.get("peggedUSD", 0.0)

            metrics.append(
                OnChainMetric(
                    metric_name="stablecoin_supply",
                    asset="ALL",
                    value=total_supply,
                    source="defillama",
                    timestamp=now,
                )
            )

            # Historical chart for weekly change
            resp_chart = await client.get(STABLECOIN_CHARTS_URL)
            resp_chart.raise_for_status()
            chart_data = resp_chart.json()

            if len(chart_data) >= 8:
                # Each entry has a "date" (unix) and "totalCirculating" etc.
                latest = chart_data[-1]
                week_ago = chart_data[-8]

                latest_supply = _extract_total(latest)
                week_ago_supply = _extract_total(week_ago)

                if week_ago_supply > 0:
                    weekly_change_pct = (
                        (latest_supply - week_ago_supply) / week_ago_supply * 100
                    )
                    metrics.append(
                        OnChainMetric(
                            metric_name="stablecoin_supply_weekly_change_pct",
                            asset="ALL",
                            value=weekly_change_pct,
                            source="defillama",
                            timestamp=now,
                        )
                    )

        return metrics


def _extract_total(entry: dict) -> float:
    """Extract totalCirculating peggedUSD from a chart entry."""
    total_circ = entry.get("totalCirculating", {})
    return total_circ.get("peggedUSD", 0.0)
