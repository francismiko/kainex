from fastapi import Request

from engine.portfolio.tracker import PortfolioTracker
from engine.storage.duckdb_store import DuckDBStore
from engine.storage.sqlite_store import SQLiteStore
from engine.strategies.registry import StrategyRegistry


def get_sqlite_store(request: Request) -> SQLiteStore:
    return request.app.state.sqlite_store


def get_duckdb_store(request: Request) -> DuckDBStore:
    return request.app.state.duckdb_store


def get_strategy_registry(request: Request) -> StrategyRegistry:
    return request.app.state.strategy_registry


def get_portfolio_tracker(request: Request) -> PortfolioTracker:
    if not hasattr(request.app.state, "portfolio_tracker"):
        request.app.state.portfolio_tracker = PortfolioTracker()
    return request.app.state.portfolio_tracker
