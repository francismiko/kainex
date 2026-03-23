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
class MomentumStrategy(AbstractStrategy):
    """Momentum strategy: buy/sell based on N-period return exceeding threshold."""

    name = "momentum"
    description = "Buy when N-period return > threshold, sell when < -threshold"
    timeframes = [TimeFrame.D1, TimeFrame.W1]
    markets = [Market.A_STOCK, Market.CRYPTO, Market.US_STOCK]

    def __init__(self, lookback: int = 20, threshold: float = 0.02) -> None:
        self.lookback = lookback
        self.threshold = threshold
        self.warmup_periods = lookback
        self._closes: list[float] = []

    def on_bar(self, bar: pd.Series) -> list[Signal]:
        close = bar.get("close")
        if close is None:
            return []

        self._closes.append(float(close))

        if len(self._closes) <= self.lookback:
            return []

        past_close = self._closes[-self.lookback - 1]
        if past_close == 0:
            return []

        ret = (close - past_close) / past_close

        signals: list[Signal] = []
        if ret > self.threshold:
            signals.append(
                Signal(
                    symbol=bar.get("symbol", ""),
                    signal_type=SignalType.BUY,
                    price=close,
                    quantity=1.0,
                )
            )
        elif ret < -self.threshold:
            signals.append(
                Signal(
                    symbol=bar.get("symbol", ""),
                    signal_type=SignalType.SELL,
                    price=close,
                    quantity=1.0,
                )
            )
        return signals

    def parameters(self) -> dict:
        return {
            "lookback": self.lookback,
            "threshold": self.threshold,
        }
