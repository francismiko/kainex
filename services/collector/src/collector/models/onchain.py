from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass
class OnChainMetric:
    metric_name: str  # "stablecoin_supply", "fear_greed_index", "btc_active_addresses"
    asset: str  # "BTC", "ETH", "ALL"
    value: float
    source: str  # "defillama", "alternative_me", "blockchain_info"
    timestamp: datetime
