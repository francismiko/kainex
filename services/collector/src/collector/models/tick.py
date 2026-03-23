from datetime import datetime

from pydantic import BaseModel

from .bar import Market


class Tick(BaseModel):
    symbol: str
    market: Market
    price: float
    volume: float
    bid: float
    ask: float
    timestamp: datetime

    model_config = {"frozen": True}
