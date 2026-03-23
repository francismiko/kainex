import itertools
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException

from engine.api.deps import get_duckdb_store, get_sqlite_store, get_strategy_registry
from engine.api.schemas.backtest import (
    BacktestListItem,
    BacktestMetrics,
    BacktestRequest,
    BacktestResponse,
    BacktestTrade,
    OptimizeRequest,
    OptimizeResponse,
    OptimizeResultItem,
)
from engine.core.backtest import BacktestEngine
from engine.storage.duckdb_store import DuckDBStore
from engine.storage.sqlite_store import SQLiteStore
from engine.strategies.base import Market
from engine.strategies.registry import StrategyRegistry

router = APIRouter()


def _market_enum(market_str: str) -> Market:
    mapping = {
        "crypto": Market.CRYPTO,
        "a_stock": Market.A_STOCK,
        "us_stock": Market.US_STOCK,
    }
    return mapping.get(market_str, Market.CRYPTO)


@router.post("/run", response_model=BacktestResponse)
async def run_backtest(
    req: BacktestRequest,
    registry: StrategyRegistry = Depends(get_strategy_registry),
    sqlite_store: SQLiteStore = Depends(get_sqlite_store),
    duckdb_store: DuckDBStore = Depends(get_duckdb_store),
):
    bid = uuid.uuid4().hex[:12]
    now = datetime.now(timezone.utc)

    # Get strategy from registry if available, otherwise use strategy_id as class name
    strategy_class_name = req.strategy_id
    sqlite_cfg = await sqlite_store.get_strategy_config(req.strategy_id)
    if sqlite_cfg:
        strategy_class_name = sqlite_cfg["class_name"]

    # Load historical data from DuckDB
    symbol = req.symbols[0] if req.symbols else "BTC/USDT"
    timeframe = "1d"
    df = duckdb_store.query_bars(
        symbol=symbol,
        market=req.market,
        timeframe=timeframe,
        start=req.start_date.isoformat() if req.start_date else None,
        end=req.end_date.isoformat() if req.end_date else None,
    )

    if df.empty:
        # No historical data available — return empty result with message
        metrics = BacktestMetrics()
        result_dict = {
            "id": bid,
            "strategy_id": req.strategy_id,
            "parameters": req.parameters or {},
            "market": req.market,
            "start_date": req.start_date.isoformat(),
            "end_date": req.end_date.isoformat(),
            "initial_capital": req.initial_capital,
            "metrics": metrics.model_dump(),
            "equity_curve": [],
            "trade_count": 0,
            "status": "completed",
            "created_at": now.isoformat(),
        }
        await sqlite_store.save_backtest_result(result_dict)
        return BacktestResponse(
            id=bid,
            strategy_id=req.strategy_id,
            status="completed",
            equity_curve=[],
            trades=[],
            metrics=metrics,
            created_at=now,
        )

    # Run backtest with real engine
    market = _market_enum(req.market)
    engine = BacktestEngine(initial_capital=req.initial_capital, market=market)

    try:
        strategy_cls = registry.get(strategy_class_name)
        params = req.parameters or (sqlite_cfg["parameters"] if sqlite_cfg else {})
        strategy_instance = strategy_cls(**params)
    except KeyError:
        raise HTTPException(
            status_code=400,
            detail=f"Strategy class '{strategy_class_name}' not registered",
        )

    bt_result = engine.run(
        strategy=strategy_instance,
        data=df,
        start=req.start_date,
        end=req.end_date,
    )

    # Convert results
    equity_list = (
        bt_result.equity_curve.tolist() if len(bt_result.equity_curve) > 0 else []
    )
    metrics = (
        BacktestMetrics(**bt_result.metrics) if bt_result.metrics else BacktestMetrics()
    )

    trades_list = []
    if not bt_result.trades.empty:
        for _, tr in bt_result.trades.iterrows():
            trades_list.append(
                BacktestTrade(
                    entry_time=tr.get("entry_time", req.start_date),
                    exit_time=tr.get("exit_time"),
                    symbol=tr.get("symbol", symbol),
                    side=tr.get("side", "buy"),
                    entry_price=tr.get("entry_price", 0.0),
                    exit_price=tr.get("exit_price"),
                    quantity=tr.get("quantity", 0.0),
                    pnl=tr.get("pnl", 0.0),
                )
            )

    # Persist result to SQLite
    result_dict = {
        "id": bid,
        "strategy_id": req.strategy_id,
        "parameters": req.parameters or {},
        "market": req.market,
        "start_date": req.start_date.isoformat(),
        "end_date": req.end_date.isoformat(),
        "initial_capital": req.initial_capital,
        "metrics": metrics.model_dump(),
        "equity_curve": equity_list,
        "trade_count": len(trades_list),
        "status": "completed",
        "created_at": now.isoformat(),
    }
    await sqlite_store.save_backtest_result(result_dict)

    return BacktestResponse(
        id=bid,
        strategy_id=req.strategy_id,
        status="completed",
        equity_curve=equity_list,
        trades=trades_list,
        metrics=metrics,
        created_at=now,
    )


@router.get("/results", response_model=list[BacktestListItem])
async def list_backtest_results(
    store: SQLiteStore = Depends(get_sqlite_store),
):
    rows = await store.list_backtest_results()
    items = []
    for row in rows:
        items.append(
            BacktestListItem(
                id=row["id"],
                strategy_id=row["strategy_id"],
                status=row.get("status", "completed"),
                metrics=BacktestMetrics(**row.get("metrics", {})),
                created_at=row["created_at"],
            )
        )
    return items


@router.get("/results/{result_id}", response_model=BacktestResponse)
async def get_backtest_result(
    result_id: str,
    store: SQLiteStore = Depends(get_sqlite_store),
):
    row = await store.get_backtest_result(result_id)
    if not row:
        raise HTTPException(
            status_code=404, detail=f"Backtest result '{result_id}' not found"
        )

    trades = []  # Individual trade data not stored in DB summary
    return BacktestResponse(
        id=row["id"],
        strategy_id=row["strategy_id"],
        status=row.get("status", "completed"),
        equity_curve=row.get("equity_curve", []),
        trades=trades,
        metrics=BacktestMetrics(**row.get("metrics", {})),
        created_at=row["created_at"],
    )


@router.post("/optimize", response_model=OptimizeResponse)
async def optimize_parameters(
    req: OptimizeRequest,
    registry: StrategyRegistry = Depends(get_strategy_registry),
    sqlite_store: SQLiteStore = Depends(get_sqlite_store),
    duckdb_store: DuckDBStore = Depends(get_duckdb_store),
):
    # Resolve strategy class
    strategy_class_name = req.strategy_id
    sqlite_cfg = await sqlite_store.get_strategy_config(req.strategy_id)
    if sqlite_cfg:
        strategy_class_name = sqlite_cfg["class_name"]

    try:
        strategy_cls = registry.get(strategy_class_name)
    except KeyError:
        raise HTTPException(
            status_code=400,
            detail=f"Strategy class '{strategy_class_name}' not registered",
        )

    # Load historical data
    symbol = req.symbols[0] if req.symbols else "BTC/USDT"
    timeframe = "1d"
    df = duckdb_store.query_bars(
        symbol=symbol,
        market=req.market,
        timeframe=timeframe,
        start=req.start_date.isoformat() if req.start_date else None,
        end=req.end_date.isoformat() if req.end_date else None,
    )

    if df.empty:
        raise HTTPException(
            status_code=400,
            detail="No historical data available for the given parameters",
        )

    # Build parameter combinations
    keys = list(req.param_grid.keys())
    values = list(req.param_grid.values())
    combos = list(itertools.product(*values))
    total_combinations = len(combos)

    # Run grid search
    market = _market_enum(req.market)
    scored: list[tuple[dict, dict, float]] = []
    for combo in combos:
        params = dict(zip(keys, combo))
        engine = BacktestEngine(initial_capital=req.initial_capital, market=market)
        strategy_instance = strategy_cls(**params)
        bt_result = engine.run(
            strategy=strategy_instance,
            data=df,
            start=req.start_date,
            end=req.end_date,
        )
        metrics = bt_result.metrics or {}
        metric_val = metrics.get(req.metric, 0.0)
        scored.append((params, metrics, metric_val))

    # Sort by metric descending (higher is better)
    scored.sort(key=lambda x: x[2], reverse=True)

    results = []
    for rank, (params, metrics, _) in enumerate(scored, start=1):
        results.append(
            OptimizeResultItem(
                parameters=params,
                metrics=BacktestMetrics(**metrics) if metrics else BacktestMetrics(),
                rank=rank,
            )
        )

    best_parameters = scored[0][0] if scored else {}

    return OptimizeResponse(
        results=results,
        best_parameters=best_parameters,
        total_combinations=total_combinations,
    )
