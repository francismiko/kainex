from dataclasses import dataclass
from datetime import datetime, timezone


@dataclass
class PortfolioSnapshot:
    timestamp: datetime
    cash: float
    positions: dict[str, float]  # symbol -> market value
    total_value: float


class PortfolioTracker:
    """Tracks real-time portfolio state."""

    def __init__(self, initial_cash: float = 100_000.0) -> None:
        self.cash = initial_cash
        self.positions: dict[str, float] = {}  # symbol -> quantity
        self.prices: dict[str, float] = {}  # symbol -> latest price
        self._snapshots: list[PortfolioSnapshot] = []

    def update_price(self, symbol: str, price: float) -> None:
        self.prices[symbol] = price

    def update_position(self, symbol: str, quantity: float) -> None:
        if quantity == 0:
            self.positions.pop(symbol, None)
        else:
            self.positions[symbol] = quantity

    @property
    def total_value(self) -> float:
        position_value = sum(
            qty * self.prices.get(sym, 0.0) for sym, qty in self.positions.items()
        )
        return self.cash + position_value

    def snapshot(self) -> PortfolioSnapshot:
        snap = PortfolioSnapshot(
            timestamp=datetime.now(timezone.utc),
            cash=self.cash,
            positions={
                sym: qty * self.prices.get(sym, 0.0)
                for sym, qty in self.positions.items()
            },
            total_value=self.total_value,
        )
        self._snapshots.append(snap)
        return snap

    @property
    def history(self) -> list[PortfolioSnapshot]:
        return list(self._snapshots)
