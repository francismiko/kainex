import numpy as np
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
class PairsTradingStrategy(AbstractStrategy):
    """Pairs trading: exploit mean reversion in the price ratio of two correlated assets."""

    name = "pairs_trading"
    description = (
        "Trade the spread between two correlated assets based on z-score of their price ratio"
    )
    timeframes = [TimeFrame.H1, TimeFrame.H4, TimeFrame.D1]
    markets = [Market.A_STOCK, Market.CRYPTO, Market.US_STOCK]

    def __init__(
        self,
        symbol_a: str = "A",
        symbol_b: str = "B",
        lookback: int = 60,
        entry_zscore: float = 2.0,
        exit_zscore: float = 0.5,
    ) -> None:
        self.symbol_a = symbol_a
        self.symbol_b = symbol_b
        self.lookback = lookback
        self.entry_zscore = entry_zscore
        self.exit_zscore = exit_zscore
        self.warmup_periods = lookback
        self._ratios: list[float] = []
        self._position: int = 0  # 0=flat, 1=long A/short B, -1=short A/long B

    def on_bar(self, bar: pd.Series) -> list[Signal]:
        price_a = bar.get("price_a")
        price_b = bar.get("price_b")
        if price_a is None or price_b is None or price_b == 0:
            return []

        ratio = float(price_a) / float(price_b)
        self._ratios.append(ratio)

        if len(self._ratios) < self.lookback:
            return []

        window = self._ratios[-self.lookback :]
        mean = float(np.mean(window))
        std = float(np.std(window, ddof=1))
        if std == 0:
            return []

        z = (ratio - mean) / std

        signals: list[Signal] = []
        close = bar.get("close", price_a)

        if z > self.entry_zscore and self._position != -1:
            # Ratio too high: short A, long B
            signals.append(
                Signal(
                    symbol=self.symbol_a,
                    signal_type=SignalType.SELL,
                    price=float(price_a),
                    quantity=1.0,
                )
            )
            signals.append(
                Signal(
                    symbol=self.symbol_b,
                    signal_type=SignalType.BUY,
                    price=float(price_b),
                    quantity=1.0,
                )
            )
            self._position = -1

        elif z < -self.entry_zscore and self._position != 1:
            # Ratio too low: long A, short B
            signals.append(
                Signal(
                    symbol=self.symbol_a,
                    signal_type=SignalType.BUY,
                    price=float(price_a),
                    quantity=1.0,
                )
            )
            signals.append(
                Signal(
                    symbol=self.symbol_b,
                    signal_type=SignalType.SELL,
                    price=float(price_b),
                    quantity=1.0,
                )
            )
            self._position = 1

        elif abs(z) < self.exit_zscore and self._position != 0:
            # Mean reverted: flatten
            if self._position == 1:
                signals.append(
                    Signal(
                        symbol=self.symbol_a,
                        signal_type=SignalType.SELL,
                        price=float(price_a),
                        quantity=1.0,
                    )
                )
                signals.append(
                    Signal(
                        symbol=self.symbol_b,
                        signal_type=SignalType.BUY,
                        price=float(price_b),
                        quantity=1.0,
                    )
                )
            else:  # _position == -1
                signals.append(
                    Signal(
                        symbol=self.symbol_a,
                        signal_type=SignalType.BUY,
                        price=float(price_a),
                        quantity=1.0,
                    )
                )
                signals.append(
                    Signal(
                        symbol=self.symbol_b,
                        signal_type=SignalType.SELL,
                        price=float(price_b),
                        quantity=1.0,
                    )
                )
            self._position = 0

        return signals

    def parameters(self) -> dict:
        return {
            "symbol_a": self.symbol_a,
            "symbol_b": self.symbol_b,
            "lookback": self.lookback,
            "entry_zscore": self.entry_zscore,
            "exit_zscore": self.exit_zscore,
        }
