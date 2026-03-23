"""Pydantic schemas for trade attribution analysis."""

from datetime import datetime

from pydantic import BaseModel


class AttributionRequest(BaseModel):
    """Request body for ``POST /api/backtest/attribution``."""

    backtest_id: str
    signal_type: str = "unknown"


class PortfolioAttributionRequest(BaseModel):
    """Request body for ``GET /api/portfolio/attribution`` query params."""

    signal_type: str = "unknown"
    limit: int = 100


# ---- Single trade attribution ----


class TradeAttributionItem(BaseModel):
    """Attribution breakdown for one trade."""

    trade_id: str
    symbol: str
    pnl: float
    signal_type: str
    market_regime: str
    entry_timing: str
    exit_timing: str
    holding_period_hours: float
    slippage_cost: float
    commission_cost: float


# ---- Summary sub-models ----


class RegimeStats(BaseModel):
    count: int
    win_rate: float
    avg_pnl: float


class SignalStats(BaseModel):
    count: int
    win_rate: float


class TimingCounts(BaseModel):
    good: int = 0
    neutral: int = 0
    bad: int = 0


class TimingQuality(BaseModel):
    entry: TimingCounts
    exit: TimingCounts


class CostAnalysis(BaseModel):
    total_slippage: float
    total_commission: float
    cost_as_pct_of_pnl: float


class AttributionSummary(BaseModel):
    by_regime: dict[str, RegimeStats]
    by_signal: dict[str, SignalStats]
    timing_quality: TimingQuality
    cost_analysis: CostAnalysis


# ---- Top-level response ----


class AttributionResponse(BaseModel):
    """Response for attribution endpoints."""

    attributions: list[TradeAttributionItem]
    summary: AttributionSummary
