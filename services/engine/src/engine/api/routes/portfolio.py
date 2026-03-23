from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Query

from engine.api.deps import get_portfolio_tracker
from engine.api.schemas.portfolio import (
    PerformanceMetrics,
    PortfolioSummary,
    PositionItem,
    TradeRecord,
)
from engine.portfolio.tracker import PortfolioTracker

router = APIRouter()


@router.get("/summary", response_model=PortfolioSummary)
async def get_portfolio_summary(
    tracker: PortfolioTracker = Depends(get_portfolio_tracker),
):
    positions = []
    for sym, qty in tracker.positions.items():
        price = tracker.prices.get(sym, 0.0)
        entry_price = price * 0.95  # mock entry price
        positions.append(
            PositionItem(
                symbol=sym,
                market="crypto",
                side="long" if qty > 0 else "short",
                quantity=abs(qty),
                entry_price=entry_price,
                current_price=price,
                unrealized_pnl=(price - entry_price) * abs(qty),
            )
        )
    return PortfolioSummary(
        total_value=tracker.total_value,
        cash=tracker.cash,
        positions=positions,
        total_pnl=tracker.total_value - 100_000.0,
        daily_pnl=0.0,
    )


@router.get("/positions", response_model=list[PositionItem])
async def get_positions(
    tracker: PortfolioTracker = Depends(get_portfolio_tracker),
):
    positions = []
    for sym, qty in tracker.positions.items():
        price = tracker.prices.get(sym, 0.0)
        entry_price = price * 0.95
        positions.append(
            PositionItem(
                symbol=sym,
                market="crypto",
                side="long" if qty > 0 else "short",
                quantity=abs(qty),
                entry_price=entry_price,
                current_price=price,
                unrealized_pnl=(price - entry_price) * abs(qty),
            )
        )
    return positions


@router.get("/trades", response_model=list[TradeRecord])
async def get_trades(
    offset: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=500),
):
    # Mock trade records - will be replaced with real ledger data
    mock_trades = [
        TradeRecord(
            id="TXN-00000001",
            strategy="sma_crossover",
            symbol="BTC/USDT",
            market="crypto",
            side="buy",
            price=30000.0,
            quantity=0.5,
            commission=15.0,
            pnl=0.0,
            timestamp=datetime(2025, 1, 15, 10, 30, 0, tzinfo=timezone.utc),
        ),
        TradeRecord(
            id="TXN-00000002",
            strategy="sma_crossover",
            symbol="BTC/USDT",
            market="crypto",
            side="sell",
            price=35000.0,
            quantity=0.5,
            commission=17.5,
            pnl=2467.5,
            timestamp=datetime(2025, 2, 20, 14, 0, 0, tzinfo=timezone.utc),
        ),
    ]
    return mock_trades[offset : offset + limit]


@router.get("/performance", response_model=PerformanceMetrics)
async def get_performance():
    # Mock performance metrics
    return PerformanceMetrics(
        sharpe_ratio=1.35,
        sortino_ratio=1.90,
        max_drawdown=-0.12,
        win_rate=0.58,
        profit_factor=1.75,
        annual_return=0.22,
        total_return=0.45,
        total_trades=42,
    )
