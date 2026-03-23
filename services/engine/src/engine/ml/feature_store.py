import pandas as pd

from engine.indicators.technical import TechnicalIndicators


class FeatureStore:
    """Builds feature matrices for ML models from raw OHLCV data."""

    def __init__(self) -> None:
        self.ti = TechnicalIndicators()

    def build_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Generate a feature DataFrame from OHLCV data."""
        features = pd.DataFrame(index=df.index)
        close = df["close"]

        features["return_1"] = close.pct_change(1)
        features["return_5"] = close.pct_change(5)
        features["return_20"] = close.pct_change(20)
        features["volatility_20"] = features["return_1"].rolling(20).std()

        features["sma_10"] = self.ti.sma(close, 10)
        features["sma_50"] = self.ti.sma(close, 50)
        features["rsi_14"] = self.ti.rsi(close, 14)

        macd = self.ti.macd(close)
        if macd is not None:
            features["macd"] = macd.iloc[:, 0]
            features["macd_signal"] = macd.iloc[:, 1]
            features["macd_hist"] = macd.iloc[:, 2]

        features["volume_ratio"] = df["volume"] / df["volume"].rolling(20).mean()

        return features.dropna()
