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
class BollingerBreakout(AbstractStrategy):
    """Bollinger Bands breakout: buy above upper band, sell below lower band."""

    name = "bollinger_breakout"
    description = (
        "Buy when price breaks above upper Bollinger Band, sell below lower band"
    )
    timeframes = [TimeFrame.M15, TimeFrame.H1, TimeFrame.H4]
    markets = [Market.A_STOCK, Market.CRYPTO, Market.US_STOCK]

    def __init__(self, bb_period: int = 20, bb_std: float = 2.0) -> None:
        self.bb_period = bb_period
        self.bb_std = bb_std
        self.warmup_periods = bb_period

    def on_bar(self, bar: pd.Series) -> list[Signal]:
        upper = bar.get("bb_upper")
        lower = bar.get("bb_lower")
        close = bar.get("close")
        if upper is None or lower is None or close is None:
            return []

        signals: list[Signal] = []
        if close > upper:
            signals.append(
                Signal(
                    symbol=bar.get("symbol", ""),
                    signal_type=SignalType.BUY,
                    price=close,
                    quantity=1.0,
                )
            )
        elif close < lower:
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
            "bb_period": self.bb_period,
            "bb_std": self.bb_std,
        }
