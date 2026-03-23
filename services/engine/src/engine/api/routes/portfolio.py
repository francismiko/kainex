import uuid

from fastapi import APIRouter, Depends, HTTPException, Query

from engine.api.deps import get_duckdb_store, get_portfolio_tracker, get_sqlite_store
from engine.api.schemas.attribution import (
    AttributionResponse,
    AttributionSummary,
    CostAnalysis,
    RegimeStats,
    SignalStats,
    TimingCounts,
    TimingQuality,
    TradeAttributionItem,
)
from engine.api.schemas.portfolio import (
    PerformanceMetrics,
    PortfolioSummary,
    PositionItem,
    TradeNote,
    TradeNoteCreate,
    TradeRecord,
)
from engine.core.attribution import AttributionAnalyzer
from engine.core.regime_detector import RegimeDetector
from engine.portfolio.tracker import PortfolioTracker
from engine.storage.duckdb_store import DuckDBStore
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


@router.post("/trades/{trade_id}/notes", response_model=TradeNote, status_code=201)
async def create_trade_note(
    trade_id: str,
    body: TradeNoteCreate,
    store: SQLiteStore = Depends(get_sqlite_store),
):
    # Verify trade exists
    cursor = await store.db.execute("SELECT id FROM trades WHERE id = ?", (trade_id,))
    row = await cursor.fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Trade not found")
    note_id = str(uuid.uuid4())
    note = await store.create_trade_note(note_id, trade_id, body.content)
    return TradeNote(**note)


@router.get("/trades/{trade_id}/notes", response_model=list[TradeNote])
async def get_trade_notes(
    trade_id: str,
    store: SQLiteStore = Depends(get_sqlite_store),
):
    notes = await store.list_trade_notes(trade_id)
    return [TradeNote(**n) for n in notes]


@router.get("/attribution", response_model=AttributionResponse)
async def portfolio_attribution(
    signal_type: str = Query("unknown", description="Signal type label for trades"),
    limit: int = Query(100, ge=1, le=1000, description="Max trades to analyze"),
    store: SQLiteStore = Depends(get_sqlite_store),
    duckdb_store: DuckDBStore = Depends(get_duckdb_store),
):
    """Run attribution analysis on live/paper trading history."""
    import pandas as pd

    rows = await store.list_trades(limit=limit, offset=0)
    if not rows:
        raise HTTPException(
            status_code=400,
            detail="No trades available for attribution analysis",
        )

    # Pair buy/sell rows into round-trip trades
    trades: list[dict] = []
    pending_buy: dict | None = None
    for row in rows:
        side = row["side"]
        if side == "buy":
            pending_buy = row
        elif side == "sell" and pending_buy is not None:
            price_buy = pending_buy.get("filled_price") or pending_buy["price"]
            price_sell = row.get("filled_price") or row["price"]
            qty = pending_buy["quantity"]
            pnl = row.get("pnl", (price_sell - price_buy) * qty)
            trades.append({
                "trade_id": pending_buy["id"],
                "symbol": pending_buy["symbol"],
                "side": "buy",
                "entry_time": pending_buy["created_at"],
                "exit_time": row["created_at"],
                "entry_price": price_buy,
                "exit_price": price_sell,
                "pnl": pnl,
                "signal_type": signal_type,
                "slippage_cost": 0.0,
                "commission_cost": pending_buy.get("commission", 0.0)
                + row.get("commission", 0.0),
            })
            pending_buy = None

    if not trades:
        raise HTTPException(
            status_code=400,
            detail="No completed round-trip trades found for attribution",
        )

    # Load market data covering the trade period
    first_entry = min(t["entry_time"] for t in trades)
    last_exit = max(t["exit_time"] for t in trades)
    symbol = trades[0]["symbol"]

    df = duckdb_store.query_bars(
        symbol=symbol,
        market="crypto",
        timeframe="1d",
        start=str(first_entry),
        end=str(last_exit),
    )

    if df.empty:
        raise HTTPException(
            status_code=400,
            detail="No market data available for the trade period",
        )

    detector = RegimeDetector()
    analyzer = AttributionAnalyzer(regime_detector=detector)

    attributions = analyzer.analyze_trades(trades, df)
    raw_summary = analyzer.summarize(attributions)

    items = [
        TradeAttributionItem(
            trade_id=a.trade_id,
            symbol=a.symbol,
            pnl=a.pnl,
            signal_type=a.signal_type,
            market_regime=a.market_regime,
            entry_timing=a.entry_timing,
            exit_timing=a.exit_timing,
            holding_period_hours=a.holding_period_hours,
            slippage_cost=a.slippage_cost,
            commission_cost=a.commission_cost,
        )
        for a in attributions
    ]

    summary = AttributionSummary(
        by_regime={
            k: RegimeStats(**v) for k, v in raw_summary["by_regime"].items()
        },
        by_signal={
            k: SignalStats(**v) for k, v in raw_summary["by_signal"].items()
        },
        timing_quality=TimingQuality(
            entry=TimingCounts(**raw_summary["timing_quality"]["entry"]),
            exit=TimingCounts(**raw_summary["timing_quality"]["exit"]),
        ),
        cost_analysis=CostAnalysis(**raw_summary["cost_analysis"]),
    )

    return AttributionResponse(attributions=items, summary=summary)
