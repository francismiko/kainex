from datetime import datetime

from pydantic import BaseModel


class PositionItem(BaseModel):
    symbol: str
    market: str
    side: str
    quantity: float
    entry_price: float
    current_price: float
    unrealized_pnl: float


class PortfolioSummary(BaseModel):
    total_value: float
    cash: float
    positions: list[PositionItem]
    total_pnl: float
    daily_pnl: float


class TradeRecord(BaseModel):
    id: str
    strategy: str
    symbol: str
    market: str
    side: str
    price: float
    quantity: float
    commission: float
    pnl: float
    timestamp: datetime


class PerformanceMetrics(BaseModel):
    sharpe_ratio: float
    sortino_ratio: float
    max_drawdown: float
    win_rate: float
    profit_factor: float
    annual_return: float
    total_return: float
    total_trades: int


class PortfolioResponse(BaseModel):
    cash: float
    positions: dict[str, float]
    total_value: float
