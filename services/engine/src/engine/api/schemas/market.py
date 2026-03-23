from datetime import datetime

from pydantic import BaseModel


class BarData(BaseModel):
    symbol: str
    market: str
    timeframe: str
    open: float
    high: float
    low: float
    close: float
    volume: float
    timestamp: datetime


class MarketDataQuery(BaseModel):
    symbol: str
    market: str = "crypto"
    timeframe: str = "1d"
    start: datetime | None = None
    end: datetime | None = None
    limit: int = 100


class LatestQuote(BaseModel):
    symbol: str
    market: str
    price: float
    change_24h: float
    volume_24h: float
    timestamp: datetime


class SymbolInfo(BaseModel):
    symbol: str
    market: str
    base: str
    quote: str
    status: str = "active"


class MarketDataResponse(BaseModel):
    symbol: str
    timeframe: str
    bars: list[BarData] = []
