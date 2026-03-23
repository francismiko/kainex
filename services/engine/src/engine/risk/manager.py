from engine.risk.drawdown import DrawdownCircuitBreaker
from engine.risk.position import PositionLimiter
from engine.strategies.base import Signal


class RiskManager:
    """Centralized risk management that gates order submission."""

    def __init__(
        self,
        max_position_pct: float = 0.1,
        max_drawdown: float = 0.2,
    ) -> None:
        self.position_limiter = PositionLimiter(max_position_pct=max_position_pct)
        self.drawdown_breaker = DrawdownCircuitBreaker(threshold=max_drawdown)
        self._halted = False

    def check(self, signal: Signal, portfolio_value: float, position_value: float) -> bool:
        """Return True if the signal passes all risk checks."""
        if self._halted:
            return False
        if not self.position_limiter.check(signal, portfolio_value, position_value):
            return False
        return True

    def update_equity(self, current_equity: float, peak_equity: float) -> None:
        """Update drawdown state; may trigger halt."""
        if self.drawdown_breaker.is_breached(current_equity, peak_equity):
            self._halted = True

    @property
    def is_halted(self) -> bool:
        return self._halted

    def reset(self) -> None:
        self._halted = False
