import itertools
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException

from engine.api.deps import get_duckdb_store, get_sqlite_store, get_strategy_registry
from engine.api.schemas.attribution import (
    AttributionRequest,
    AttributionResponse,
    AttributionSummary,
    CostAnalysis,
    RegimeStats,
    SignalStats,
    TimingCounts,
    TimingQuality,
    TradeAttributionItem,
)
from engine.api.schemas.backtest import (
    BacktestListItem,
    BacktestMetrics,
    BacktestRequest,
    BacktestResponse,
    BacktestTrade,
    OptimizeRequest,
    OptimizeResponse,
    OptimizeResultItem,
    WalkForwardRequest,
    WalkForwardResponse,
    WalkForwardWindowResponse,
)
from engine.core.attribution import AttributionAnalyzer
from engine.core.backtest import BacktestEngine
from engine.core.regime_detector import RegimeDetector
from engine.core.walk_forward import WalkForwardOptimizer
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


@router.post("/walk-forward", response_model=WalkForwardResponse)
async def walk_forward_optimize(
    req: WalkForwardRequest,
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

    market = _market_enum(req.market)
    engine = BacktestEngine(initial_capital=req.initial_capital, market=market)
    optimizer = WalkForwardOptimizer(
        backtest_engine=engine,
        n_splits=req.n_splits,
        train_pct=req.train_pct,
    )

    try:
        wf_result = optimizer.optimize(
            strategy_cls=strategy_cls,
            data=df,
            param_grid=req.param_grid,
            metric=req.metric,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    windows = [
        WalkForwardWindowResponse(
            train_start=w.train_start,
            train_end=w.train_end,
            test_start=w.test_start,
            test_end=w.test_end,
            best_params=w.best_params,
            train_metrics=w.train_metrics,
            test_metrics=w.test_metrics,
        )
        for w in wf_result.windows
    ]

    return WalkForwardResponse(
        windows=windows,
        overall_test_metrics=wf_result.overall_test_metrics,
        overfitting_score=wf_result.overfitting_score,
        is_overfit=wf_result.is_overfit,
    )


# --------------- Attribution ---------------


def _build_attribution_response(
    analyzer: AttributionAnalyzer,
    trades: list[dict],
    data,
) -> AttributionResponse:
    """Run attribution analysis and convert to the API response model."""
    import pandas as pd

    attributions = analyzer.analyze_trades(trades, data)
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


@router.post("/attribution", response_model=AttributionResponse)
async def backtest_attribution(
    req: AttributionRequest,
    registry: StrategyRegistry = Depends(get_strategy_registry),
    sqlite_store: SQLiteStore = Depends(get_sqlite_store),
    duckdb_store: DuckDBStore = Depends(get_duckdb_store),
):
    """Run attribution analysis on a previously completed backtest."""
    import pandas as pd

    row = await sqlite_store.get_backtest_result(req.backtest_id)
    if not row:
        raise HTTPException(
            status_code=404,
            detail=f"Backtest result '{req.backtest_id}' not found",
        )

    # Re-run the backtest to get trade details (they are not stored in the DB summary)
    strategy_class_name = row["strategy_id"]
    sqlite_cfg = await sqlite_store.get_strategy_config(row["strategy_id"])
    if sqlite_cfg:
        strategy_class_name = sqlite_cfg["class_name"]

    symbol = "BTC/USDT"
    market_str = row.get("market", "crypto")
    timeframe = "1d"
    df = duckdb_store.query_bars(
        symbol=symbol,
        market=market_str,
        timeframe=timeframe,
        start=row.get("start_date"),
        end=row.get("end_date"),
    )

    if df.empty:
        raise HTTPException(
            status_code=400,
            detail="No historical data available for attribution analysis",
        )

    market = _market_enum(market_str)
    engine = BacktestEngine(
        initial_capital=row.get("initial_capital", 100_000.0),
        market=market,
    )

    try:
        strategy_cls = registry.get(strategy_class_name)
        params = row.get("parameters", {})
        strategy_instance = strategy_cls(**params)
    except KeyError:
        raise HTTPException(
            status_code=400,
            detail=f"Strategy class '{strategy_class_name}' not registered",
        )

    bt_result = engine.run(strategy=strategy_instance, data=df)

    if bt_result.trades.empty:
        raise HTTPException(
            status_code=400,
            detail="Backtest produced no trades for attribution analysis",
        )

    # Convert DataFrame rows to dicts and inject signal_type from request
    trades = []
    for idx, tr in bt_result.trades.iterrows():
        trades.append({
            "trade_id": str(idx),
            "symbol": tr.get("symbol", symbol),
            "side": tr.get("side", "buy"),
            "entry_time": tr.get("entry_time"),
            "exit_time": tr.get("exit_time"),
            "entry_price": tr.get("entry_price", 0.0),
            "exit_price": tr.get("exit_price", 0.0),
            "pnl": tr.get("pnl", 0.0),
            "signal_type": req.signal_type,
            "slippage_cost": 0.0,
            "commission_cost": 0.0,
        })

    detector = RegimeDetector()
    analyzer = AttributionAnalyzer(regime_detector=detector)
    return _build_attribution_response(analyzer, trades, df)
