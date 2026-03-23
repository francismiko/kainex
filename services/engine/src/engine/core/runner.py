import pandas as pd

from engine.strategies.base import AbstractStrategy, Signal


class StrategyRunner:
    """Orchestrates strategy execution across market data."""

    def __init__(self, strategy: AbstractStrategy) -> None:
        self.strategy = strategy
        self._signals: list[Signal] = []
        self._bar_count: int = 0

    @property
    def signals(self) -> list[Signal]:
        return list(self._signals)

    def feed(self, bar: pd.Series) -> list[Signal]:
        """Feed a single bar and collect signals."""
        self._bar_count += 1
        if self._bar_count <= self.strategy.warmup_periods:
            return []
        new_signals = self.strategy.on_bar(bar)
        self._signals.extend(new_signals)
        return new_signals

    def run(self, data: pd.DataFrame) -> list[Signal]:
        """Run strategy over a full DataFrame of bars."""
        self._signals.clear()
        self._bar_count = 0
        for _, bar in data.iterrows():
            self.feed(bar)
        return self.signals

    def reset(self) -> None:
        self._signals.clear()
        self._bar_count = 0
