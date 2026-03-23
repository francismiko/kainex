from datetime import datetime
from enum import Enum

from pydantic import BaseModel


class Market(str, Enum):
    A_STOCK = "a_stock"
    CRYPTO = "crypto"
    US_STOCK = "us_stock"


class TimeFrame(str, Enum):
    TICK = "tick"
    M1 = "1m"
    M5 = "5m"
    M15 = "15m"
    H1 = "1h"
    H4 = "4h"
    D1 = "1d"
    W1 = "1w"


class Bar(BaseModel):
    symbol: str
    market: Market
    timeframe: TimeFrame
    open: float
    high: float
    low: float
    close: float
    volume: float
    timestamp: datetime

    model_config = {"frozen": True}
