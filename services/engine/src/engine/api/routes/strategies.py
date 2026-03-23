import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException

from engine.api.deps import get_strategy_registry
from engine.api.schemas.strategy import (
    StrategyCreate,
    StrategyDetail,
    StrategyListItem,
    StrategyUpdate,
)
from engine.strategies.registry import StrategyRegistry

router = APIRouter()

# In-memory store for strategy configurations
_strategy_configs: dict[str, dict] = {}


@router.get("/", response_model=list[StrategyListItem])
async def list_strategies(
    registry: StrategyRegistry = Depends(get_strategy_registry),
):
    items: list[StrategyListItem] = []
    for sid, cfg in _strategy_configs.items():
        items.append(
            StrategyListItem(
                id=sid,
                name=cfg["name"],
                class_name=cfg["class_name"],
                markets=cfg["markets"],
                timeframes=cfg["timeframes"],
                status=cfg.get("status", "stopped"),
                created_at=cfg["created_at"],
            )
        )
    return items


@router.get("/{strategy_id}", response_model=StrategyDetail)
async def get_strategy(
    strategy_id: str,
    registry: StrategyRegistry = Depends(get_strategy_registry),
):
    cfg = _strategy_configs.get(strategy_id)
    if not cfg:
        raise HTTPException(status_code=404, detail=f"Strategy '{strategy_id}' not found")
    return StrategyDetail(
        id=strategy_id,
        name=cfg["name"],
        class_name=cfg["class_name"],
        markets=cfg["markets"],
        timeframes=cfg["timeframes"],
        status=cfg.get("status", "stopped"),
        parameters=cfg.get("parameters", {}),
        created_at=cfg["created_at"],
        updated_at=cfg.get("updated_at"),
    )


@router.post("/", response_model=StrategyDetail, status_code=201)
async def create_strategy(
    req: StrategyCreate,
    registry: StrategyRegistry = Depends(get_strategy_registry),
):
    # Validate class_name exists in registry
    try:
        registry.get(req.class_name)
    except KeyError:
        raise HTTPException(
            status_code=400,
            detail=f"Strategy class '{req.class_name}' not registered",
        )

    sid = uuid.uuid4().hex[:12]
    now = datetime.now(timezone.utc)
    cfg = {
        "name": req.name,
        "class_name": req.class_name,
        "parameters": req.parameters,
        "markets": req.markets,
        "timeframes": req.timeframes,
        "status": "stopped",
        "created_at": now,
        "updated_at": now,
    }
    _strategy_configs[sid] = cfg
    return StrategyDetail(
        id=sid,
        name=cfg["name"],
        class_name=cfg["class_name"],
        markets=cfg["markets"],
        timeframes=cfg["timeframes"],
        status=cfg["status"],
        parameters=cfg["parameters"],
        created_at=cfg["created_at"],
        updated_at=cfg["updated_at"],
    )


@router.put("/{strategy_id}", response_model=StrategyDetail)
async def update_strategy(
    strategy_id: str,
    req: StrategyUpdate,
):
    cfg = _strategy_configs.get(strategy_id)
    if not cfg:
        raise HTTPException(status_code=404, detail=f"Strategy '{strategy_id}' not found")

    if req.parameters is not None:
        cfg["parameters"] = req.parameters
    if req.status is not None:
        cfg["status"] = req.status
    cfg["updated_at"] = datetime.now(timezone.utc)

    return StrategyDetail(
        id=strategy_id,
        name=cfg["name"],
        class_name=cfg["class_name"],
        markets=cfg["markets"],
        timeframes=cfg["timeframes"],
        status=cfg.get("status", "stopped"),
        parameters=cfg.get("parameters", {}),
        created_at=cfg["created_at"],
        updated_at=cfg["updated_at"],
    )


@router.post("/{strategy_id}/start", response_model=StrategyDetail)
async def start_strategy(strategy_id: str):
    cfg = _strategy_configs.get(strategy_id)
    if not cfg:
        raise HTTPException(status_code=404, detail=f"Strategy '{strategy_id}' not found")

    cfg["status"] = "running"
    cfg["updated_at"] = datetime.now(timezone.utc)

    return StrategyDetail(
        id=strategy_id,
        name=cfg["name"],
        class_name=cfg["class_name"],
        markets=cfg["markets"],
        timeframes=cfg["timeframes"],
        status=cfg["status"],
        parameters=cfg.get("parameters", {}),
        created_at=cfg["created_at"],
        updated_at=cfg["updated_at"],
    )


@router.post("/{strategy_id}/stop", response_model=StrategyDetail)
async def stop_strategy(strategy_id: str):
    cfg = _strategy_configs.get(strategy_id)
    if not cfg:
        raise HTTPException(status_code=404, detail=f"Strategy '{strategy_id}' not found")

    cfg["status"] = "stopped"
    cfg["updated_at"] = datetime.now(timezone.utc)

    return StrategyDetail(
        id=strategy_id,
        name=cfg["name"],
        class_name=cfg["class_name"],
        markets=cfg["markets"],
        timeframes=cfg["timeframes"],
        status=cfg["status"],
        parameters=cfg.get("parameters", {}),
        created_at=cfg["created_at"],
        updated_at=cfg["updated_at"],
    )
