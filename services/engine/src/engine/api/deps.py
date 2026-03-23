from fastapi import Request

from engine.portfolio.tracker import PortfolioTracker
from engine.strategies.registry import StrategyRegistry, registry as strategy_registry


def get_strategy_registry() -> StrategyRegistry:
    return strategy_registry


def get_portfolio_tracker(request: Request) -> PortfolioTracker:
    if not hasattr(request.app.state, "portfolio_tracker"):
        request.app.state.portfolio_tracker = PortfolioTracker()
    return request.app.state.portfolio_tracker


def get_redis(request: Request):
    return request.app.state.redis


def get_db(request: Request):
    return request.app.state.db
