from datetime import datetime
from enum import Enum

from pydantic import BaseModel


class AlertCondition(str, Enum):
    above = "above"
    below = "below"
    cross_above = "cross_above"
    cross_below = "cross_below"


class AlertCreate(BaseModel):
    symbol: str
    market: str = "crypto"
    condition: AlertCondition
    price: float
    message: str = ""


class AlertUpdate(BaseModel):
    enabled: bool | None = None
    message: str | None = None


class AlertItem(BaseModel):
    id: str
    symbol: str
    market: str
    condition: AlertCondition
    price: float
    message: str
    enabled: bool = True
    triggered: bool = False
    created_at: datetime
    updated_at: datetime
