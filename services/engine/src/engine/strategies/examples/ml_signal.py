"""ML-driven signal strategy.

Uses :class:`~engine.ml.feature_store.FeatureStore` to compute features from
OHLCV bars and :class:`~engine.indicators.ml_predictor.MLPredictor` to
obtain a continuous prediction signal.  When the prediction exceeds
*threshold* the strategy emits a BUY; below *-threshold* it emits a SELL.
"""

from __future__ import annotations

import pandas as pd

from engine.indicators.ml_predictor import MLPredictor
from engine.ml.feature_store import FeatureStore
from engine.ml.model_registry import ModelRegistry
from engine.strategies.base import (
    AbstractStrategy,
    Market,
    Signal,
    SignalType,
    TimeFrame,
)
from engine.strategies.registry import registry


@registry.register
class MLSignalStrategy(AbstractStrategy):
    """ML prediction-based strategy (legacy bar-by-bar interface)."""

    name = "ml_signal"
    description = "Buy/sell based on ML model prediction exceeding a threshold"
    timeframes = [TimeFrame.D1, TimeFrame.H1]
    markets = [Market.A_STOCK, Market.CRYPTO, Market.US_STOCK]

    def __init__(
        self,
        model_name: str = "rf_classifier",
        threshold: float = 0.5,
        lookback: int = 60,
        model_registry: ModelRegistry | None = None,
    ) -> None:
        self.model_name = model_name
        self.threshold = threshold
        self.lookback = lookback
        self.warmup_periods = lookback

        self._feature_store = FeatureStore()
        self._predictor = MLPredictor(model_name=model_name, registry=model_registry)
        self._predictor.load()

        # Accumulate bars into an internal buffer
        self._bars: list[dict] = []

    def on_bar(self, bar: pd.Series) -> list[Signal]:
        self._bars.append(bar.to_dict())

        if len(self._bars) < self.lookback:
            return []

        # Build a DataFrame from the recent lookback window
        window = self._bars[-self.lookback :]
        df = pd.DataFrame(window)

        # Ensure required columns exist
        required = {"open", "high", "low", "close", "volume"}
        if not required.issubset(df.columns):
            return []

        # Set a simple integer index if there is no datetime index
        if "timestamp" in df.columns:
            df["timestamp"] = pd.to_datetime(df["timestamp"])
            df = df.set_index("timestamp")
        else:
            df.index = pd.RangeIndex(len(df))

        features = self._feature_store.compute_features(df)
        if features.empty:
            return []

        signal_series = self._predictor.predict(features)
        if signal_series.empty:
            return []

        last_signal = float(signal_series.iloc[-1])
        symbol = bar.get("symbol", "")
        close = float(bar.get("close", 0.0))

        signals: list[Signal] = []
        if last_signal > self.threshold:
            signals.append(
                Signal(
                    symbol=symbol,
                    signal_type=SignalType.BUY,
                    price=close,
                    quantity=1.0,
                )
            )
        elif last_signal < -self.threshold:
            signals.append(
                Signal(
                    symbol=symbol,
                    signal_type=SignalType.SELL,
                    price=close,
                    quantity=1.0,
                )
            )
        return signals

    def parameters(self) -> dict:
        return {
            "model_name": self.model_name,
            "threshold": self.threshold,
            "lookback": self.lookback,
        }
