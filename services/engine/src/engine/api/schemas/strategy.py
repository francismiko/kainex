from datetime import datetime

from pydantic import BaseModel


class StrategyInfo(BaseModel):
    name: str
    description: str
    timeframes: list[str]
    markets: list[str]


class StrategyListResponse(BaseModel):
    strategies: list[StrategyInfo]


class StrategyPerformanceSummary(BaseModel):
    total_return: float = 0.0
    sharpe_ratio: float = 0.0
    max_drawdown: float = 0.0
    win_rate: float = 0.0


class StrategyListItem(BaseModel):
    id: str
    name: str
    class_name: str
    markets: list[str]
    timeframes: list[str]
    status: str = "stopped"
    created_at: datetime


class StrategyDetail(BaseModel):
    id: str
    name: str
    class_name: str
    markets: list[str]
    timeframes: list[str]
    status: str = "stopped"
    parameters: dict = {}
    performance: StrategyPerformanceSummary = StrategyPerformanceSummary()
    created_at: datetime
    updated_at: datetime | None = None


class StrategyCreate(BaseModel):
    name: str
    class_name: str
    parameters: dict = {}
    markets: list[str]
    timeframes: list[str]


class StrategyUpdate(BaseModel):
    parameters: dict | None = None
    status: str | None = None
