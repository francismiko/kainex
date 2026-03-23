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
class MacdCrossover(AbstractStrategy):
    """MACD crossover: buy when MACD crosses above signal, sell on cross below."""

    name = "macd_crossover"
    description = "Buy when MACD line crosses above signal line, sell on cross below"
    timeframes = [TimeFrame.H1, TimeFrame.H4, TimeFrame.D1]
    markets = [Market.A_STOCK, Market.CRYPTO, Market.US_STOCK]

    def __init__(
        self,
        fast_period: int = 12,
        slow_period: int = 26,
        signal_period: int = 9,
    ) -> None:
        self.fast_period = fast_period
        self.slow_period = slow_period
        self.signal_period = signal_period
        self.warmup_periods = slow_period + signal_period
        self._prev_macd: float | None = None
        self._prev_signal: float | None = None

    def on_bar(self, bar: pd.Series) -> list[Signal]:
        macd_val = bar.get("macd")
        signal_val = bar.get("macd_signal")
        if macd_val is None or signal_val is None:
            return []

        signals: list[Signal] = []
        if self._prev_macd is not None and self._prev_signal is not None:
            if self._prev_macd <= self._prev_signal and macd_val > signal_val:
                signals.append(
                    Signal(
                        symbol=bar.get("symbol", ""),
                        signal_type=SignalType.BUY,
                        price=bar["close"],
                        quantity=1.0,
                    )
                )
            elif self._prev_macd >= self._prev_signal and macd_val < signal_val:
                signals.append(
                    Signal(
                        symbol=bar.get("symbol", ""),
                        signal_type=SignalType.SELL,
                        price=bar["close"],
                        quantity=1.0,
                    )
                )

        self._prev_macd = macd_val
        self._prev_signal = signal_val
        return signals

    def parameters(self) -> dict:
        return {
            "fast_period": self.fast_period,
            "slow_period": self.slow_period,
            "signal_period": self.signal_period,
        }
