from dataclasses import dataclass

import numpy as np
import pandas as pd


@dataclass
class Prediction:
    symbol: str
    direction: float  # positive = bullish, negative = bearish
    confidence: float  # 0.0 ~ 1.0
    horizon: int  # bars ahead


class MLPredictor:
    """Interface for ML model inference in the strategy pipeline."""

    def __init__(self, model_name: str | None = None) -> None:
        self.model_name = model_name
        self._model = None

    def load(self, model_path: str) -> None:
        """Load a serialized model from disk."""
        # TODO: implement model loading (joblib / ONNX / torch)
        pass

    def predict(self, features: pd.DataFrame) -> list[Prediction]:
        """Run inference on a feature DataFrame."""
        if self._model is None:
            # Return neutral predictions when no model loaded
            return [
                Prediction(
                    symbol="",
                    direction=0.0,
                    confidence=0.0,
                    horizon=1,
                )
            ]
        raise NotImplementedError("Model inference not yet implemented")

    def predict_proba(self, features: pd.DataFrame) -> np.ndarray:
        """Return class probabilities."""
        if self._model is None:
            return np.array([0.5, 0.5])
        raise NotImplementedError
