import uuid

from fastapi import APIRouter, Depends, HTTPException

from engine.api.deps import get_sqlite_store
from engine.api.schemas.alert import AlertCreate, AlertItem, AlertUpdate
from engine.storage.sqlite_store import SQLiteStore

router = APIRouter()


@router.post("", response_model=AlertItem, status_code=201)
async def create_alert(
    body: AlertCreate,
    store: SQLiteStore = Depends(get_sqlite_store),
):
    alert_id = uuid.uuid4().hex[:12]
    alert_dict = {
        "id": alert_id,
        "symbol": body.symbol,
        "market": body.market,
        "condition": body.condition.value,
        "price": body.price,
        "message": body.message,
        "enabled": True,
    }
    await store.create_alert(alert_dict)
    created = await store.get_alert(alert_id)
    if not created:
        raise HTTPException(status_code=500, detail="Failed to create alert")
    return created


@router.get("", response_model=list[AlertItem])
async def list_alerts(
    store: SQLiteStore = Depends(get_sqlite_store),
):
    return await store.list_alerts()


@router.delete("/{alert_id}", status_code=204)
async def delete_alert(
    alert_id: str,
    store: SQLiteStore = Depends(get_sqlite_store),
):
    deleted = await store.delete_alert(alert_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Alert not found")
    return None


@router.patch("/{alert_id}", response_model=AlertItem)
async def update_alert(
    alert_id: str,
    body: AlertUpdate,
    store: SQLiteStore = Depends(get_sqlite_store),
):
    existing = await store.get_alert(alert_id)
    if not existing:
        raise HTTPException(status_code=404, detail="Alert not found")

    fields = body.model_dump(exclude_none=True)
    if fields:
        await store.update_alert(alert_id, fields)

    updated = await store.get_alert(alert_id)
    return updated
