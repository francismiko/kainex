import asyncio
import logging
from collections import deque
from datetime import datetime, timezone

from fastapi import APIRouter, Query

from engine.api.schemas.log import LogEntry

router = APIRouter()
logger = logging.getLogger(__name__)

# In-memory log store (ring buffer, max 1000 entries)
_log_store: deque[LogEntry] = deque(maxlen=1000)

# Listeners waiting for new log entries (for WebSocket broadcast)
_listeners: list[asyncio.Queue[LogEntry]] = []


def add_log(
    level: str,
    source: str,
    message: str,
    metadata: dict | None = None,
) -> LogEntry:
    """Append a log entry and notify all listeners."""
    entry = LogEntry(
        timestamp=datetime.now(timezone.utc).isoformat(),
        level=level.upper(),
        source=source,
        message=message,
        metadata=metadata,
    )
    _log_store.append(entry)
    for q in _listeners:
        try:
            q.put_nowait(entry)
        except asyncio.QueueFull:
            pass  # drop if consumer is too slow
    return entry


def subscribe_logs() -> asyncio.Queue[LogEntry]:
    """Create a queue that receives new log entries in real time."""
    q: asyncio.Queue[LogEntry] = asyncio.Queue(maxsize=256)
    _listeners.append(q)
    return q


def unsubscribe_logs(q: asyncio.Queue[LogEntry]) -> None:
    """Remove a listener queue."""
    try:
        _listeners.remove(q)
    except ValueError:
        pass


@router.get("/", response_model=list[LogEntry])
async def list_logs(
    level: str | None = Query(None, description="Filter by log level (INFO, WARNING, ERROR)"),
    strategy_id: str | None = Query(None, description="Filter by strategy source"),
    limit: int = Query(100, ge=1, le=1000, description="Max entries to return"),
    offset: int = Query(0, ge=0, description="Number of entries to skip"),
):
    """Return stored log entries with optional filters."""
    entries = list(_log_store)

    if level:
        entries = [e for e in entries if e.level == level.upper()]
    if strategy_id:
        entries = [e for e in entries if e.source == strategy_id]

    # Most recent first
    entries.reverse()
    return entries[offset : offset + limit]


@router.get("/strategies/{strategy_id}", response_model=list[LogEntry])
async def get_strategy_logs(
    strategy_id: str,
    level: str | None = Query(None, description="Filter by log level"),
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
):
    """Return logs for a specific strategy."""
    entries = [e for e in _log_store if e.source == strategy_id]

    if level:
        entries = [e for e in entries if e.level == level.upper()]

    entries.reverse()
    return entries[offset : offset + limit]
