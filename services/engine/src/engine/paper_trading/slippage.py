import random

from engine.strategies.base import SignalType


class SlippageModel:
    """Simulates market slippage on order fills."""

    def __init__(self, rate: float = 0.001, seed: int | None = None) -> None:
        self.rate = rate
        self._rng = random.Random(seed)

    def apply(self, price: float, side: SignalType) -> float:
        """Apply random slippage to an order price."""
        slip = self._rng.uniform(0, self.rate) * price
        if side == SignalType.BUY:
            return price + slip  # buy at slightly higher
        elif side == SignalType.SELL:
            return price - slip  # sell at slightly lower
        return price
