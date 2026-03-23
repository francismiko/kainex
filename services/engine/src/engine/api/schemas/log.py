from pydantic import BaseModel


class LogEntry(BaseModel):
    timestamp: str
    level: str  # INFO, WARNING, ERROR
    source: str  # strategy_id or "system"
    message: str
    metadata: dict | None = None
