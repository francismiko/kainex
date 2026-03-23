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
class RsiMeanReversion(AbstractStrategy):
    """RSI mean reversion: buy when oversold, sell when overbought."""

    name = "rsi_mean_reversion"
    description = (
        "Buy when RSI < oversold threshold, sell when RSI > overbought threshold"
    )
    timeframes = [TimeFrame.H1, TimeFrame.H4, TimeFrame.D1]
    markets = [Market.A_STOCK, Market.CRYPTO, Market.US_STOCK]

    def __init__(
        self,
        rsi_period: int = 14,
        oversold: float = 30.0,
        overbought: float = 70.0,
    ) -> None:
        self.rsi_period = rsi_period
        self.oversold = oversold
        self.overbought = overbought
        self.warmup_periods = rsi_period + 1

    def on_bar(self, bar: pd.Series) -> list[Signal]:
        rsi = bar.get("rsi")
        if rsi is None:
            return []

        signals: list[Signal] = []
        if rsi < self.oversold:
            signals.append(
                Signal(
                    symbol=bar.get("symbol", ""),
                    signal_type=SignalType.BUY,
                    price=bar["close"],
                    quantity=1.0,
                )
            )
        elif rsi > self.overbought:
            signals.append(
                Signal(
                    symbol=bar.get("symbol", ""),
                    signal_type=SignalType.SELL,
                    price=bar["close"],
                    quantity=1.0,
                )
            )
        return signals

    def parameters(self) -> dict:
        return {
            "rsi_period": self.rsi_period,
            "oversold": self.oversold,
            "overbought": self.overbought,
        }
