import pandas as pd

from engine.strategies.base import (
    AbstractStrategy,
    Market,
    Signal,
    SignalType,
    TimeFrame,
)
from engine.strategies.registry import registry


@registry.register
class GridTradingStrategy(AbstractStrategy):
    """Grid trading: place buy/sell orders at fixed price intervals around a base price."""

    name = "grid_trading"
    description = (
        "Set a grid of price levels and buy low / sell high as price oscillates"
    )
    timeframes = [TimeFrame.M1, TimeFrame.M5, TimeFrame.M15]
    markets = [Market.CRYPTO]

    def __init__(
        self,
        grid_size: float = 0.02,
        num_grids: int = 10,
        base_price: float = 0.0,
    ) -> None:
        self.grid_size = grid_size
        self.num_grids = num_grids
        self.base_price = base_price
        self.warmup_periods = 0
        self._grid_lines: list[float] = []
        self._last_grid_index: int | None = None
        self._initialized: bool = False

    def _init_grid(self, price: float) -> None:
        """Build grid lines around the base price."""
        base = self.base_price if self.base_price > 0 else price
        half = self.num_grids // 2
        self._grid_lines = [
            base * (1 + self.grid_size * i) for i in range(-half, half + 1)
        ]
        self._grid_lines.sort()
        self._last_grid_index = self._find_grid_index(price)
        self._initialized = True

    def _find_grid_index(self, price: float) -> int:
        """Return the index of the highest grid line <= price."""
        idx = 0
        for i, level in enumerate(self._grid_lines):
            if level <= price:
                idx = i
            else:
                break
        return idx

    def on_bar(self, bar: pd.Series) -> list[Signal]:
        close = bar.get("close")
        if close is None:
            return []

        close = float(close)

        if not self._initialized:
            self._init_grid(close)
            return []

        current_index = self._find_grid_index(close)

        if current_index == self._last_grid_index:
            return []

        signals: list[Signal] = []
        symbol = bar.get("symbol", "")

        if current_index < self._last_grid_index:
            # Price dropped through grid line(s): buy
            signals.append(
                Signal(
                    symbol=symbol,
                    signal_type=SignalType.BUY,
                    price=close,
                    quantity=1.0,
                )
            )
        elif current_index > self._last_grid_index:
            # Price rose through grid line(s): sell
            signals.append(
                Signal(
                    symbol=symbol,
                    signal_type=SignalType.SELL,
                    price=close,
                    quantity=1.0,
                )
            )

        self._last_grid_index = current_index
        return signals

    def parameters(self) -> dict:
        return {
            "grid_size": self.grid_size,
            "num_grids": self.num_grids,
            "base_price": self.base_price,
        }
