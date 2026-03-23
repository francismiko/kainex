import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException

from engine.api.schemas.backtest import (
    BacktestListItem,
    BacktestMetrics,
    BacktestRequest,
    BacktestResponse,
    BacktestTrade,
)

router = APIRouter()

# In-memory store for backtest results
_backtest_results: dict[str, dict] = {}


@router.post("/run", response_model=BacktestResponse)
async def run_backtest(req: BacktestRequest):
    bid = uuid.uuid4().hex[:12]
    now = datetime.now(timezone.utc)

    # TODO: integrate with BacktestEngine for real execution
    # For now, return mock result structure
    metrics = BacktestMetrics(
        sharpe_ratio=1.25,
        sortino_ratio=1.80,
        max_drawdown=-0.15,
        win_rate=0.55,
        profit_factor=1.65,
        annual_return=0.18,
        total_return=0.35,
    )

    mock_trades = [
        BacktestTrade(
            entry_time=req.start_date,
            exit_time=req.end_date,
            symbol=req.symbols[0] if req.symbols else "BTC/USDT",
            side="buy",
            entry_price=30000.0,
            exit_price=40500.0,
            quantity=1.0,
            pnl=10500.0,
        ),
    ]

    result = {
        "id": bid,
        "strategy_id": req.strategy_id,
        "status": "completed",
        "equity_curve": [100000.0, 102000.0, 105000.0, 103000.0, 110000.0, 135000.0],
        "trades": [t.model_dump() for t in mock_trades],
        "metrics": metrics.model_dump(),
        "created_at": now,
    }
    _backtest_results[bid] = result

    return BacktestResponse(
        id=bid,
        strategy_id=req.strategy_id,
        status="completed",
        equity_curve=result["equity_curve"],
        trades=mock_trades,
        metrics=metrics,
        created_at=now,
    )


@router.get("/results", response_model=list[BacktestListItem])
async def list_backtest_results():
    items: list[BacktestListItem] = []
    for bid, res in _backtest_results.items():
        items.append(
            BacktestListItem(
                id=bid,
                strategy_id=res["strategy_id"],
                status=res["status"],
                metrics=BacktestMetrics(**res["metrics"]),
                created_at=res["created_at"],
            )
        )
    return items


@router.get("/results/{result_id}", response_model=BacktestResponse)
async def get_backtest_result(result_id: str):
    res = _backtest_results.get(result_id)
    if not res:
        raise HTTPException(status_code=404, detail=f"Backtest result '{result_id}' not found")
    return BacktestResponse(
        id=res["id"],
        strategy_id=res["strategy_id"],
        status=res["status"],
        equity_curve=res["equity_curve"],
        trades=[BacktestTrade(**t) for t in res["trades"]],
        metrics=BacktestMetrics(**res["metrics"]),
        created_at=res["created_at"],
    )
