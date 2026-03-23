"""ML inference interface for the strategy pipeline.

Wraps a scikit-learn (or compatible) model loaded through
:class:`~engine.ml.model_registry.ModelRegistry`, exposing ``predict``
(continuous signal) and ``predict_signal`` (discrete :class:`SignalType`)
methods.  When no model is loaded, every call returns a neutral prediction
so that downstream consumers never crash.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass

import numpy as np
import pandas as pd

from kainex_shared import SignalType

from engine.ml.model_registry import ModelRegistry

logger = logging.getLogger(__name__)


@dataclass
class Prediction:
    symbol: str
    direction: float  # positive = bullish, negative = bearish
    confidence: float  # 0.0 ~ 1.0
    horizon: int  # bars ahead


class MLPredictor:
    """Interface for ML model inference in the strategy pipeline."""

    def __init__(
        self,
        model_name: str | None = None,
        registry: ModelRegistry | None = None,
    ) -> None:
        self.model_name = model_name
        self._registry = registry
        self._model = None

    # ------------------------------------------------------------------
    # Loading
    # ------------------------------------------------------------------

    def load(self, model_name: str | None = None) -> None:
        """Load a model from the :class:`ModelRegistry`.

        Parameters
        ----------
        model_name : str, optional
            Override the model name set during construction.
        """
        name = model_name or self.model_name
        if name is None:
            logger.warning(
                "No model name specified; predictor will return neutral signals."
            )
            return

        if self._registry is None:
            self._registry = ModelRegistry()

        try:
            self._model = self._registry.load(name)
            self.model_name = name
            logger.info("Loaded model '%s' for inference.", name)
        except FileNotFoundError:
            logger.warning(
                "Model '%s' not found in registry; using neutral predictor.", name
            )
            self._model = None

    # ------------------------------------------------------------------
    # Inference
    # ------------------------------------------------------------------

    def predict(self, features: pd.DataFrame) -> pd.Series:
        """Return continuous prediction signal in the range ``[-1, 1]``.

        - Positive values indicate a bullish signal.
        - Negative values indicate a bearish signal.
        - Zero means neutral.

        If no model is loaded, returns a Series of zeros.
        """
        if self._model is None:
            return pd.Series(0.0, index=features.index, name="ml_signal")

        try:
            # Attempt predict_proba for classifiers (buy/sell/hold -> 3 classes)
            if hasattr(self._model, "predict_proba"):
                proba = self._model.predict_proba(features)
                classes = list(self._model.classes_)
                # Map class probabilities to a continuous signal:
                #   signal = P(buy) - P(sell)
                # Expect classes to be integers: 1=buy, -1=sell, 0=hold
                buy_idx = classes.index(1) if 1 in classes else None
                sell_idx = classes.index(-1) if -1 in classes else None
                if buy_idx is not None and sell_idx is not None:
                    signal = proba[:, buy_idx] - proba[:, sell_idx]
                else:
                    # Fallback for binary classifiers
                    signal = proba[:, -1] * 2 - 1
            else:
                # Regressors return the signal directly
                raw = self._model.predict(features)
                signal = np.clip(raw, -1, 1)

            return pd.Series(signal, index=features.index, name="ml_signal")
        except Exception:
            logger.exception("Prediction failed; returning neutral signal.")
            return pd.Series(0.0, index=features.index, name="ml_signal")

    def predict_signal(self, features: pd.DataFrame) -> SignalType:
        """Return a discrete signal for the *last* row of features.

        Uses the same model as :meth:`predict` but collapses the continuous
        output to a :class:`SignalType`.
        """
        signal = self.predict(features)
        if signal.empty:
            return SignalType.HOLD

        last = float(signal.iloc[-1])
        if last > 0.0:
            return SignalType.BUY
        elif last < 0.0:
            return SignalType.SELL
        return SignalType.HOLD

    def predict_proba(self, features: pd.DataFrame) -> np.ndarray:
        """Return class probabilities (for classifiers)."""
        if self._model is None:
            n = len(features) if len(features) > 0 else 1
            return np.full((n, 3), 1 / 3)
        try:
            return self._model.predict_proba(features)
        except Exception:
            logger.exception("predict_proba failed; returning uniform distribution.")
            n = len(features) if len(features) > 0 else 1
            return np.full((n, 3), 1 / 3)
