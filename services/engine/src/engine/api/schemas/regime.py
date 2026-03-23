"""Pydantic schemas for market regime detection and strategy recommendation."""

from pydantic import BaseModel


class RegimeResponse(BaseModel):
    """Response for ``GET /api/market-data/regime``."""

    symbol: str
    regime: str
    confidence: float
    reason: str


class StrategyRecommendResponse(BaseModel):
    """Response for ``GET /api/strategies/recommend``."""

    symbol: str
    regime: str
    confidence: float
    recommended_strategies: list[str]
    reason: str


class RuleResult(BaseModel):
    regime: str
    confidence: float
    recommended_strategies: list[str]
    reason: str


class MlResult(BaseModel):
    regime: str
    confidence: float
    recommended_strategies: list[str]
    reason: str


class FullAnalysisResponse(BaseModel):
    """Response for ``GET /api/strategies/recommend/full``."""

    symbol: str
    rule_based: RuleResult
    ml_based: MlResult
    consensus: bool
