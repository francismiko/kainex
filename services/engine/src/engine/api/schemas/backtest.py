from datetime import datetime

from pydantic import BaseModel


class BacktestRequest(BaseModel):
    strategy_id: str
    parameters: dict | None = None
    start_date: datetime
    end_date: datetime
    initial_capital: float = 100_000.0
    market: str = "crypto"
    symbols: list[str] = ["BTC/USDT"]


class BacktestMetrics(BaseModel):
    sharpe_ratio: float = 0.0
    sortino_ratio: float = 0.0
    max_drawdown: float = 0.0
    win_rate: float = 0.0
    profit_factor: float = 0.0
    annual_return: float = 0.0
    total_return: float = 0.0


class BacktestTrade(BaseModel):
    entry_time: datetime
    exit_time: datetime | None = None
    symbol: str
    side: str
    entry_price: float
    exit_price: float | None = None
    quantity: float
    pnl: float = 0.0


class BacktestResponse(BaseModel):
    id: str
    strategy_id: str
    status: str = "completed"
    equity_curve: list[float] = []
    trades: list[BacktestTrade] = []
    metrics: BacktestMetrics = BacktestMetrics()
    created_at: datetime


class BacktestListItem(BaseModel):
    id: str
    strategy_id: str
    status: str
    metrics: BacktestMetrics
    created_at: datetime


class OptimizeRequest(BaseModel):
    strategy_id: str
    param_grid: dict[str, list]
    start_date: datetime
    end_date: datetime
    initial_capital: float = 100_000.0
    market: str = "crypto"
    symbols: list[str] = ["BTC/USDT"]
    metric: str = "sharpe_ratio"


class OptimizeResultItem(BaseModel):
    parameters: dict
    metrics: BacktestMetrics
    rank: int


class OptimizeResponse(BaseModel):
    results: list[OptimizeResultItem]
    best_parameters: dict
    total_combinations: int
