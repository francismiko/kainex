class DrawdownCircuitBreaker:
    """Halts trading when drawdown exceeds a threshold."""

    def __init__(self, threshold: float = 0.2) -> None:
        self.threshold = threshold

    def is_breached(self, current_equity: float, peak_equity: float) -> bool:
        """Return True if drawdown from peak exceeds threshold."""
        if peak_equity <= 0:
            return False
        drawdown = (peak_equity - current_equity) / peak_equity
        return drawdown >= self.threshold

    def current_drawdown(self, current_equity: float, peak_equity: float) -> float:
        if peak_equity <= 0:
            return 0.0
        return (peak_equity - current_equity) / peak_equity
