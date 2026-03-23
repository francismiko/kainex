from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum


class TradeType(str, Enum):
    BUY = "buy"
    SELL = "sell"


@dataclass
class TradeRecord:
    id: str
    symbol: str
    trade_type: TradeType
    quantity: float
    price: float
    commission: float
    timestamp: datetime
    pnl: float = 0.0
    metadata: dict = field(default_factory=dict)


class Ledger:
    """Immutable trade journal."""

    def __init__(self) -> None:
        self._records: list[TradeRecord] = []
        self._counter: int = 0

    def record(
        self,
        symbol: str,
        trade_type: TradeType,
        quantity: float,
        price: float,
        commission: float,
        pnl: float = 0.0,
        metadata: dict | None = None,
    ) -> TradeRecord:
        self._counter += 1
        rec = TradeRecord(
            id=f"TXN-{self._counter:08d}",
            symbol=symbol,
            trade_type=trade_type,
            quantity=quantity,
            price=price,
            commission=commission,
            timestamp=datetime.now(),
            pnl=pnl,
            metadata=metadata or {},
        )
        self._records.append(rec)
        return rec

    @property
    def records(self) -> list[TradeRecord]:
        return list(self._records)

    def by_symbol(self, symbol: str) -> list[TradeRecord]:
        return [r for r in self._records if r.symbol == symbol]

    @property
    def total_commission(self) -> float:
        return sum(r.commission for r in self._records)

    @property
    def total_pnl(self) -> float:
        return sum(r.pnl for r in self._records)
