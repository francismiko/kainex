from fastapi import APIRouter, Depends, Query

from engine.api.deps import get_portfolio_tracker, get_sqlite_store
from engine.api.schemas.portfolio import (
    PerformanceMetrics,
    PortfolioSummary,
    PositionItem,
    TradeRecord,
)
from engine.portfolio.tracker import PortfolioTracker
from engine.storage.sqlite_store import SQLiteStore

router = APIRouter()


@router.get("/summary", response_model=PortfolioSummary)
async def get_portfolio_summary(
    tracker: PortfolioTracker = Depends(get_portfolio_tracker),
):
    positions = []
    for sym, qty in tracker.positions.items():
        price = tracker.prices.get(sym, 0.0)
        entry_price = price * 0.95 if price > 0 else 0.0
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
    store: SQLiteStore = Depends(get_sqlite_store),
):
    # Try to get positions from SQLite
    cursor = await store.db.execute("SELECT * FROM positions ORDER BY updated_at DESC")
    rows = await cursor.fetchall()
    if rows:
        positions = []
        for row in rows:
            row_dict = dict(row)
            qty = row_dict.get("quantity", 0.0)
            avg_price = row_dict.get("avg_price", 0.0)
            market_price = row_dict.get("market_price", 0.0)
            positions.append(
                PositionItem(
                    symbol=row_dict["symbol"],
                    market="crypto",
                    side="long" if qty > 0 else "short",
                    quantity=abs(qty),
                    entry_price=avg_price,
                    current_price=market_price,
                    unrealized_pnl=row_dict.get("unrealized_pnl", 0.0),
                )
            )
        return positions

    # Fallback to in-memory tracker
    positions = []
    for sym, qty in tracker.positions.items():
        price = tracker.prices.get(sym, 0.0)
        entry_price = price * 0.95 if price > 0 else 0.0
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
    store: SQLiteStore = Depends(get_sqlite_store),
):
    rows = await store.list_trades(limit=limit, offset=offset)
    trades = []
    for row in rows:
        trades.append(
            TradeRecord(
                id=row["id"],
                strategy=row.get("strategy_id", ""),
                symbol=row["symbol"],
                market="crypto",
                side=row["side"],
                price=row.get("filled_price") or row["price"],
                quantity=row["quantity"],
                commission=row.get("commission", 0.0),
                pnl=row.get("pnl", 0.0),
                timestamp=row["created_at"],
            )
        )
    return trades


@router.get("/performance", response_model=PerformanceMetrics)
async def get_performance(
    store: SQLiteStore = Depends(get_sqlite_store),
):
    # Aggregate from backtest results if available
    results = await store.list_backtest_results(limit=1)
    if results:
        latest = results[0]
        metrics = latest.get("metrics", {})
        trade_count = latest.get("trade_count", 0)
        return PerformanceMetrics(
            sharpe_ratio=metrics.get("sharpe_ratio", 0.0),
            sortino_ratio=metrics.get("sortino_ratio", 0.0),
            max_drawdown=metrics.get("max_drawdown", 0.0),
            win_rate=metrics.get("win_rate", 0.0),
            profit_factor=metrics.get("profit_factor", 0.0),
            annual_return=metrics.get("annual_return", 0.0),
            total_return=metrics.get("total_return", 0.0),
            total_trades=trade_count,
        )

    # Count trades from trade ledger
    cursor = await store.db.execute("SELECT COUNT(*) FROM trades")
    count_row = await cursor.fetchone()
    total_trades = count_row[0] if count_row else 0

    return PerformanceMetrics(
        sharpe_ratio=0.0,
        sortino_ratio=0.0,
        max_drawdown=0.0,
        win_rate=0.0,
        profit_factor=0.0,
        annual_return=0.0,
        total_return=0.0,
        total_trades=total_trades,
    )
