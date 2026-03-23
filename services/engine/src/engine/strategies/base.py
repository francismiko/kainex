from abc import ABC, abstractmethod

import pandas as pd
from kainex_shared import Market, Signal, SignalType, TimeFrame  # noqa: F401
from nautilus_trader.config import StrategyConfig
from nautilus_trader.model.data import Bar
from nautilus_trader.model.identifiers import InstrumentId
from nautilus_trader.trading.strategy import Strategy


class AbstractStrategy(ABC):
    """Legacy strategy interface for simple bar-by-bar signal generation."""

    name: str
    description: str
    timeframes: list[TimeFrame]
    markets: list[Market]
    warmup_periods: int = 0

    @abstractmethod
    def on_bar(self, bar: pd.Series) -> list[Signal]:
        """Process a new bar and return signals."""
        ...

    @abstractmethod
    def parameters(self) -> dict:
        """Return strategy parameters."""
        ...


class KainexStrategyConfig(StrategyConfig, frozen=True):
    """Base config for Kainex strategies running on NautilusTrader."""

    instrument_id: str = ""
    market: str = "crypto"


class KainexStrategy(Strategy):
    """Bridge between Kainex strategy interface and NautilusTrader Strategy.

    Subclass this and implement `on_kainex_bar()` to generate Kainex Signals,
    which are then translated into NautilusTrader orders.
    """

    name: str = ""
    description: str = ""
    timeframes: list[TimeFrame] = []
    markets: list[Market] = []

    def __init__(self, config: KainexStrategyConfig) -> None:
        super().__init__(config)
        self._config = config
        self._signals: list[Signal] = []

    @property
    def instrument(self) -> InstrumentId | None:
        if self._config.instrument_id:
            return InstrumentId.from_str(self._config.instrument_id)
        return None

    @property
    def collected_signals(self) -> list[Signal]:
        return list(self._signals)

    def on_bar(self, bar: Bar) -> None:
        """NautilusTrader callback — delegates to on_kainex_bar."""
        signals = self.on_kainex_bar(bar)
        self._signals.extend(signals)

    @abstractmethod
    def on_kainex_bar(self, bar: Bar) -> list[Signal]:
        """Process a NautilusTrader Bar and return Kainex signals."""
        ...

    @abstractmethod
    def kainex_parameters(self) -> dict:
        """Return strategy parameters."""
        ...
