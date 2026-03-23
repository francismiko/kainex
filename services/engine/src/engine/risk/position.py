from engine.strategies.base import Signal


class PositionLimiter:
    """Enforces per-position size limits as a fraction of portfolio."""

    def __init__(self, max_position_pct: float = 0.1) -> None:
        self.max_position_pct = max_position_pct

    def check(
        self,
        signal: Signal,
        portfolio_value: float,
        current_position_value: float,
    ) -> bool:
        """Return True if the order would not exceed position limits."""
        order_value = signal.price * signal.quantity
        new_position_value = current_position_value + order_value
        max_allowed = portfolio_value * self.max_position_pct
        return new_position_value <= max_allowed
