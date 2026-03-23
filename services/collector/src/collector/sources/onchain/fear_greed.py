from __future__ import annotations

import logging
from datetime import datetime, timezone

import httpx

from collector.models.onchain import OnChainMetric

logger = logging.getLogger(__name__)

FNG_URL = "https://api.alternative.me/fng/"


class FearGreedSource:
    """Fetch Fear & Greed Index from Alternative.me."""

    async def fetch_metrics(self, limit: int = 1) -> list[OnChainMetric]:
        metrics: list[OnChainMetric] = []

        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.get(
                FNG_URL, params={"limit": limit, "format": "json"}
            )
            resp.raise_for_status()
            data = resp.json()

            for entry in data.get("data", []):
                value = float(entry["value"])
                ts = datetime.fromtimestamp(
                    int(entry["timestamp"]), tz=timezone.utc
                )
                metrics.append(
                    OnChainMetric(
                        metric_name="fear_greed_index",
                        asset="BTC",
                        value=value,
                        source="alternative_me",
                        timestamp=ts,
                    )
                )

        return metrics
