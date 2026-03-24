"""Feature engineering pipeline for ML models.

Computes a comprehensive feature matrix from raw OHLCV data, including price
returns, technical indicators (via pandas-ta), volatility measures, volume
statistics, and calendar features.
"""

from __future__ import annotations

import logging

import numpy as np
import pandas as pd

import pandas_ta as ta

from engine.indicators.technical import TechnicalIndicators

logger = logging.getLogger(__name__)


class FeatureStore:
    """Builds feature matrices for ML models from raw OHLCV data."""

    def __init__(self) -> None:
        self.ti = TechnicalIndicators()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def compute_features(
        self, df: pd.DataFrame, market: str = "crypto"
    ) -> pd.DataFrame:
        """Generate a feature DataFrame from OHLCV data.

        Parameters
        ----------
        df : pd.DataFrame
            Must contain columns: open, high, low, close, volume.
            The index should be a DatetimeIndex.
        market : str
            Market identifier (used for potential market-specific features).

        Returns
        -------
        pd.DataFrame
            Feature matrix with NaN rows dropped.
        """
        features = pd.DataFrame(index=df.index)
        close = df["close"]
        high = df["high"]
        low = df["low"]
        volume = df["volume"]

        # --- Price returns ---
        features["return_1"] = close.pct_change(1)
        features["return_5"] = close.pct_change(5)
        features["return_10"] = close.pct_change(10)
        features["return_20"] = close.pct_change(20)

        features["log_return_1"] = np.log(close / close.shift(1))
        features["log_return_5"] = np.log(close / close.shift(5))

        # Price momentum (N-day)
        features["momentum_5"] = close / close.shift(5) - 1
        features["momentum_10"] = close / close.shift(10) - 1
        features["momentum_20"] = close / close.shift(20) - 1

        # --- Technical indicators (SMA) ---
        for length in (5, 10, 20, 60):
            sma = self.ti.sma(close, length=length)
            if sma is not None:
                features[f"sma_{length}"] = sma
                features[f"price_sma_{length}_ratio"] = close / sma - 1
            else:
                features[f"sma_{length}"] = np.nan
                features[f"price_sma_{length}_ratio"] = np.nan

        # --- RSI ---
        rsi = self.ti.rsi(close, length=14)
        features["rsi_14"] = rsi if rsi is not None else np.nan

        # --- MACD ---
        macd = self.ti.macd(close)
        if macd is not None:
            features["macd"] = macd.iloc[:, 0]
            features["macd_signal"] = macd.iloc[:, 1]
            features["macd_hist"] = macd.iloc[:, 2]
        else:
            features["macd"] = np.nan
            features["macd_signal"] = np.nan
            features["macd_hist"] = np.nan

        # --- ATR ---
        atr = self.ti.atr(high, low, close, length=14)
        features["atr_14"] = atr if atr is not None else np.nan

        # --- Bollinger %B ---
        bbands = self.ti.bbands(close, length=20, std=2.0)
        if bbands is not None:
            # bbands columns: BBL, BBM, BBU, BBB, BBP
            col_names = bbands.columns.tolist()
            # %B is the last column (BBP_20_2.0)
            bbp_col = [c for c in col_names if c.startswith("BBP")]
            if bbp_col:
                features["bb_percent_b"] = bbands[bbp_col[0]]
            else:
                # fallback: compute manually
                bbl = bbands.iloc[:, 0]
                bbu = bbands.iloc[:, 2]
                features["bb_percent_b"] = (close - bbl) / (bbu - bbl)
        else:
            features["bb_percent_b"] = np.nan

        # --- ADX ---
        adx_result = ta.adx(high, low, close, length=14)
        if adx_result is not None:
            features["adx_14"] = adx_result[f"ADX_14"]
            features["di_plus_14"] = adx_result[f"DMP_14"]
            features["di_minus_14"] = adx_result[f"DMN_14"]
        else:
            features["adx_14"] = np.nan
            features["di_plus_14"] = np.nan
            features["di_minus_14"] = np.nan

        # --- Volume indicators ---
        obv = ta.obv(close, volume)
        features["obv"] = obv if obv is not None else np.nan

        cmf = ta.cmf(high, low, close, volume, length=20)
        features["cmf_20"] = cmf if cmf is not None else np.nan

        mfi = ta.mfi(high, low, close, volume, length=14)
        features["mfi_14"] = mfi if mfi is not None else np.nan

        # --- Oscillators ---
        willr = ta.willr(high, low, close, length=14)
        features["willr_14"] = willr if willr is not None else np.nan

        cci = ta.cci(high, low, close, length=20)
        features["cci_20"] = cci if cci is not None else np.nan

        # --- ATR percentage ---
        features["atr_pct"] = (
            atr / close if atr is not None else np.nan
        )

        # --- VWAP ---
        if "volume" in df.columns:
            vwap = ta.vwap(high, low, close, volume)
            if vwap is not None:
                features["vwap"] = vwap
                features["price_vs_vwap"] = close / vwap - 1
            else:
                features["vwap"] = np.nan
                features["price_vs_vwap"] = np.nan

        # --- Volatility ---
        features["rolling_std_20"] = close.pct_change().rolling(20).std()
        features["realized_volatility"] = np.sqrt(
            (np.log(close / close.shift(1)) ** 2).rolling(20).sum()
        )

        # --- Volume ---
        vol_ma_20 = volume.rolling(20).mean()
        features["volume_ma_ratio"] = volume / vol_ma_20
        features["volume_std"] = volume.rolling(20).std()

        # --- Calendar / time features ---
        if isinstance(df.index, pd.DatetimeIndex):
            features["day_of_week"] = df.index.dayofweek
            features["month"] = df.index.month
            features["is_month_end"] = df.index.is_month_end.astype(int)

        return features.dropna()

    def build_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Backward-compatible alias for ``compute_features``."""
        return self.compute_features(df)

    def get_feature_names(self) -> list[str]:
        """Return the list of feature column names produced by compute_features.

        This constructs a canonical list without requiring actual data.
        """
        names: list[str] = []

        # Price returns
        names.extend(["return_1", "return_5", "return_10", "return_20"])
        names.extend(["log_return_1", "log_return_5"])
        names.extend(["momentum_5", "momentum_10", "momentum_20"])

        # SMAs
        for length in (5, 10, 20, 60):
            names.append(f"sma_{length}")
            names.append(f"price_sma_{length}_ratio")

        # Technical indicators
        names.extend(["rsi_14", "macd", "macd_signal", "macd_hist", "atr_14"])
        names.append("bb_percent_b")

        # ADX
        names.extend(["adx_14", "di_plus_14", "di_minus_14"])

        # Volume indicators
        names.extend(["obv", "cmf_20", "mfi_14"])

        # Oscillators
        names.extend(["willr_14", "cci_20"])

        # ATR percentage
        names.append("atr_pct")

        # VWAP
        names.extend(["vwap", "price_vs_vwap"])

        # Volatility
        names.extend(["rolling_std_20", "realized_volatility"])

        # Volume
        names.extend(["volume_ma_ratio", "volume_std"])

        # Calendar
        names.extend(["day_of_week", "month", "is_month_end"])

        return names
