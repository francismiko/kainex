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
class DualMaStrategy(AbstractStrategy):
    """Dual moving average strategy supporting EMA and SMA."""

    name = "dual_ma"
    description = "Buy when fast MA crosses above slow MA, sell on cross below (supports EMA/SMA)"
    timeframes = [
        TimeFrame.M1, TimeFrame.M5, TimeFrame.M15,
        TimeFrame.H1, TimeFrame.H4, TimeFrame.D1, TimeFrame.W1,
    ]
    markets = [Market.A_STOCK, Market.CRYPTO, Market.US_STOCK]

    def __init__(
        self,
        fast_period: int = 10,
        slow_period: int = 30,
        ma_type: str = "ema",
    ) -> None:
        self.fast_period = fast_period
        self.slow_period = slow_period
        self.ma_type = ma_type
        self.warmup_periods = slow_period
        self._prev_fast: float | None = None
        self._prev_slow: float | None = None

    def on_bar(self, bar: pd.Series) -> list[Signal]:
        fast_ma = bar.get("ma_fast")
        slow_ma = bar.get("ma_slow")
        if fast_ma is None or slow_ma is None:
            return []

        signals: list[Signal] = []
        if self._prev_fast is not None and self._prev_slow is not None:
            if self._prev_fast <= self._prev_slow and fast_ma > slow_ma:
                signals.append(
                    Signal(
                        symbol=bar.get("symbol", ""),
                        signal_type=SignalType.BUY,
                        price=bar["close"],
                        quantity=1.0,
                    )
                )
            elif self._prev_fast >= self._prev_slow and fast_ma < slow_ma:
                signals.append(
                    Signal(
                        symbol=bar.get("symbol", ""),
                        signal_type=SignalType.SELL,
                        price=bar["close"],
                        quantity=1.0,
                    )
                )

        self._prev_fast = fast_ma
        self._prev_slow = slow_ma
        return signals

    def parameters(self) -> dict:
        return {
            "fast_period": self.fast_period,
            "slow_period": self.slow_period,
            "ma_type": self.ma_type,
        }
