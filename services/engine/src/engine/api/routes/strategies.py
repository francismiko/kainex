import uuid

from fastapi import APIRouter, Depends, HTTPException

from engine.api.deps import get_sqlite_store, get_strategy_registry
from engine.api.schemas.strategy import (
    StrategyCreate,
    StrategyDetail,
    StrategyListItem,
    StrategyUpdate,
)
from engine.storage.sqlite_store import SQLiteStore
from engine.strategies.registry import StrategyRegistry

router = APIRouter()


def _row_to_list_item(row: dict) -> StrategyListItem:
    return StrategyListItem(
        id=row["id"],
        name=row["name"],
        class_name=row["class_name"],
        markets=row.get("markets", []),
        timeframes=row.get("timeframes", []),
        status=row.get("status", "stopped"),
        created_at=row["created_at"],
    )


def _row_to_detail(row: dict) -> StrategyDetail:
    return StrategyDetail(
        id=row["id"],
        name=row["name"],
        class_name=row["class_name"],
        markets=row.get("markets", []),
        timeframes=row.get("timeframes", []),
        status=row.get("status", "stopped"),
        parameters=row.get("parameters", {}),
        created_at=row["created_at"],
        updated_at=row.get("updated_at"),
    )


@router.get("/", response_model=list[StrategyListItem])
async def list_strategies(
    store: SQLiteStore = Depends(get_sqlite_store),
):
    rows = await store.list_strategy_configs()
    return [_row_to_list_item(r) for r in rows]


@router.get("/{strategy_id}", response_model=StrategyDetail)
async def get_strategy(
    strategy_id: str,
    store: SQLiteStore = Depends(get_sqlite_store),
):
    row = await store.get_strategy_config(strategy_id)
    if not row:
        raise HTTPException(
            status_code=404, detail=f"Strategy '{strategy_id}' not found"
        )
    return _row_to_detail(row)


@router.post("/", response_model=StrategyDetail, status_code=201)
async def create_strategy(
    req: StrategyCreate,
    registry: StrategyRegistry = Depends(get_strategy_registry),
    store: SQLiteStore = Depends(get_sqlite_store),
):
    try:
        registry.get(req.class_name)
    except KeyError:
        raise HTTPException(
            status_code=400,
            detail=f"Strategy class '{req.class_name}' not registered",
        )

    sid = uuid.uuid4().hex[:12]
    await store.save_strategy_config(
        id=sid,
        name=req.name,
        class_name=req.class_name,
        parameters=req.parameters,
        markets=req.markets,
        timeframes=req.timeframes,
    )
    row = await store.get_strategy_config(sid)
    return _row_to_detail(row)


@router.put("/{strategy_id}", response_model=StrategyDetail)
async def update_strategy(
    strategy_id: str,
    req: StrategyUpdate,
    store: SQLiteStore = Depends(get_sqlite_store),
):
    row = await store.get_strategy_config(strategy_id)
    if not row:
        raise HTTPException(
            status_code=404, detail=f"Strategy '{strategy_id}' not found"
        )

    updates: dict = {}
    if req.parameters is not None:
        updates["parameters"] = req.parameters
    if req.status is not None:
        updates["status"] = req.status
    if updates:
        await store.update_strategy_fields(strategy_id, updates)

    row = await store.get_strategy_config(strategy_id)
    return _row_to_detail(row)


@router.post("/{strategy_id}/start", response_model=StrategyDetail)
async def start_strategy(
    strategy_id: str,
    store: SQLiteStore = Depends(get_sqlite_store),
):
    row = await store.get_strategy_config(strategy_id)
    if not row:
        raise HTTPException(
            status_code=404, detail=f"Strategy '{strategy_id}' not found"
        )

    await store.update_strategy_fields(strategy_id, {"status": "running"})
    row = await store.get_strategy_config(strategy_id)
    return _row_to_detail(row)


@router.post("/{strategy_id}/stop", response_model=StrategyDetail)
async def stop_strategy(
    strategy_id: str,
    store: SQLiteStore = Depends(get_sqlite_store),
):
    row = await store.get_strategy_config(strategy_id)
    if not row:
        raise HTTPException(
            status_code=404, detail=f"Strategy '{strategy_id}' not found"
        )

    await store.update_strategy_fields(strategy_id, {"status": "stopped"})
    row = await store.get_strategy_config(strategy_id)
    return _row_to_detail(row)
