import pandas as pd

from nautilus_trader.model.data import Bar

from engine.strategies.base import (
    AbstractStrategy,
    KainexStrategy,
    KainexStrategyConfig,
    Market,
    Signal,
    SignalType,
    TimeFrame,
)
from engine.strategies.registry import registry


class SmaCrossoverConfig(KainexStrategyConfig, frozen=True):
    short_window: int = 10
    long_window: int = 30


class SmaCrossoverStrategy(KainexStrategy):
    """SMA crossover strategy using NautilusTrader."""

    name = "sma_crossover"
    description = "Buy when short SMA crosses above long SMA, sell on cross below"
    timeframes = [TimeFrame.D1, TimeFrame.H1]
    markets = [Market.A_STOCK, Market.CRYPTO, Market.US_STOCK]

    def __init__(self, config: SmaCrossoverConfig | None = None, short_window: int = 10, long_window: int = 30) -> None:
        if config is None:
            config = SmaCrossoverConfig(short_window=short_window, long_window=long_window)
        super().__init__(config)
        self.short_window = config.short_window
        self.long_window = config.long_window
        self.warmup_periods = config.long_window
        self._closes: list[float] = []
        self._prev_short: float | None = None
        self._prev_long: float | None = None

    def on_kainex_bar(self, bar: Bar) -> list[Signal]:
        self._closes.append(float(bar.close))

        if len(self._closes) < self.long_window:
            return []

        short_sma = sum(self._closes[-self.short_window:]) / self.short_window
        long_sma = sum(self._closes[-self.long_window:]) / self.long_window

        signals: list[Signal] = []
        if self._prev_short is not None and self._prev_long is not None:
            if self._prev_short <= self._prev_long and short_sma > long_sma:
                signals.append(
                    Signal(
                        symbol=str(bar.bar_type.instrument_id),
                        signal_type=SignalType.BUY,
                        price=float(bar.close),
                        quantity=1.0,
                    )
                )
            elif self._prev_short >= self._prev_long and short_sma < long_sma:
                signals.append(
                    Signal(
                        symbol=str(bar.bar_type.instrument_id),
                        signal_type=SignalType.SELL,
                        price=float(bar.close),
                        quantity=1.0,
                    )
                )

        self._prev_short = short_sma
        self._prev_long = long_sma
        return signals

    def kainex_parameters(self) -> dict:
        return {
            "short_window": self.short_window,
            "long_window": self.long_window,
        }


# Legacy adapter for backward compatibility with old bar-by-bar interface
@registry.register
class SmaCrossoverLegacy(AbstractStrategy):
    """Simple Moving Average crossover strategy (legacy bar-by-bar interface)."""

    name = "sma_crossover"
    description = "Buy when short SMA crosses above long SMA, sell on cross below"
    timeframes = [TimeFrame.D1, TimeFrame.H1]
    markets = [Market.A_STOCK, Market.CRYPTO, Market.US_STOCK]

    def __init__(self, short_window: int = 10, long_window: int = 30) -> None:
        self.short_window = short_window
        self.long_window = long_window
        self.warmup_periods = long_window
        self._prev_short: float | None = None
        self._prev_long: float | None = None

    def on_bar(self, bar: pd.Series) -> list[Signal]:
        short_sma = bar.get("sma_short")
        long_sma = bar.get("sma_long")
        if short_sma is None or long_sma is None:
            return []

        signals: list[Signal] = []
        if self._prev_short is not None and self._prev_long is not None:
            if self._prev_short <= self._prev_long and short_sma > long_sma:
                signals.append(
                    Signal(
                        symbol=bar.get("symbol", ""),
                        signal_type=SignalType.BUY,
                        price=bar["close"],
                        quantity=1.0,
                    )
                )
            elif self._prev_short >= self._prev_long and short_sma < long_sma:
                signals.append(
                    Signal(
                        symbol=bar.get("symbol", ""),
                        signal_type=SignalType.SELL,
                        price=bar["close"],
                        quantity=1.0,
                    )
                )

        self._prev_short = short_sma
        self._prev_long = long_sma
        return signals

    def parameters(self) -> dict:
        return {
            "short_window": self.short_window,
            "long_window": self.long_window,
        }
