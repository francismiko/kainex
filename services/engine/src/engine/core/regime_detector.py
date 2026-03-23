"""Market regime detection using technical indicators and ML models.

Identifies the current market state (trending, ranging, high/low volatility)
to enable adaptive strategy selection.
"""

from __future__ import annotations

import logging
from enum import Enum

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)


class MarketRegime(str, Enum):
    """Market regime classification.

    Each regime maps to a set of strategies that historically perform well
    under the corresponding market conditions.
    """

    TRENDING_UP = "trending_up"  # 上升趋势
    TRENDING_DOWN = "trending_down"  # 下降趋势
    RANGING = "ranging"  # 震荡/横盘
    HIGH_VOLATILITY = "high_volatility"  # 高波动
    LOW_VOLATILITY = "low_volatility"  # 低波动


# --------------- Technical indicator helpers ---------------


def _sma(series: pd.Series, length: int) -> pd.Series:
    """Simple moving average."""
    return series.rolling(window=length, min_periods=length).mean()


def _true_range(high: pd.Series, low: pd.Series, close: pd.Series) -> pd.Series:
    """True Range — max of (H-L, |H-prevC|, |L-prevC|)."""
    prev_close = close.shift(1)
    tr1 = high - low
    tr2 = (high - prev_close).abs()
    tr3 = (low - prev_close).abs()
    return pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)


def _atr(high: pd.Series, low: pd.Series, close: pd.Series, length: int = 14) -> pd.Series:
    """Average True Range."""
    tr = _true_range(high, low, close)
    return tr.rolling(window=length, min_periods=length).mean()


def _adx(high: pd.Series, low: pd.Series, close: pd.Series, length: int = 14) -> pd.Series:
    """Average Directional Index (ADX).

    Measures trend strength regardless of direction.
    ADX > 25 generally indicates a strong trend.
    ADX < 20 generally indicates a ranging/sideways market.
    """
    # +DM / -DM
    up_move = high.diff()
    down_move = -low.diff()

    plus_dm = pd.Series(np.where((up_move > down_move) & (up_move > 0), up_move, 0.0), index=high.index)
    minus_dm = pd.Series(np.where((down_move > up_move) & (down_move > 0), down_move, 0.0), index=high.index)

    atr_vals = _atr(high, low, close, length)

    # Smoothed +DI / -DI
    plus_di = 100 * (plus_dm.rolling(window=length, min_periods=length).mean() / atr_vals)
    minus_di = 100 * (minus_dm.rolling(window=length, min_periods=length).mean() / atr_vals)

    # DX and ADX
    dx = 100 * (plus_di - minus_di).abs() / (plus_di + minus_di).replace(0, np.nan)
    adx_series = dx.rolling(window=length, min_periods=length).mean()
    return adx_series


# --------------- Rule-based detector ---------------

# Default thresholds (can be overridden via constructor)
_DEFAULT_ADX_TREND = 25.0  # ADX above this => trending
_DEFAULT_ADX_RANGE = 20.0  # ADX below this => ranging
_DEFAULT_ATR_HIGH = 0.03  # ATR/close above this => high volatility
_DEFAULT_ATR_LOW = 0.01  # ATR/close below this => low volatility
_DEFAULT_SMA_LEN = 50
_DEFAULT_ADX_LEN = 14
_DEFAULT_ATR_LEN = 14
_MIN_BARS = 60  # Minimum bars required for reliable detection


class RegimeDetector:
    """Identify the current market regime from OHLCV data.

    Primary method: rule-based detection using ADX, ATR, and SMA.
    Secondary method: ML-based detection using Gaussian Mixture Models.
    """

    def __init__(
        self,
        adx_trend_threshold: float = _DEFAULT_ADX_TREND,
        adx_range_threshold: float = _DEFAULT_ADX_RANGE,
        atr_high_threshold: float = _DEFAULT_ATR_HIGH,
        atr_low_threshold: float = _DEFAULT_ATR_LOW,
        sma_length: int = _DEFAULT_SMA_LEN,
        adx_length: int = _DEFAULT_ADX_LEN,
        atr_length: int = _DEFAULT_ATR_LEN,
    ) -> None:
        self.adx_trend_threshold = adx_trend_threshold
        self.adx_range_threshold = adx_range_threshold
        self.atr_high_threshold = atr_high_threshold
        self.atr_low_threshold = atr_low_threshold
        self.sma_length = sma_length
        self.adx_length = adx_length
        self.atr_length = atr_length

    # ---- public API ----

    def detect(self, df: pd.DataFrame) -> MarketRegime:
        """Rule-based regime detection using ADX + ATR + SMA.

        Decision tree (evaluated in order):
        1. If ATR/close > atr_high_threshold => HIGH_VOLATILITY
        2. If ADX > adx_trend_threshold (strong trend):
           - close > SMA => TRENDING_UP
           - close <= SMA => TRENDING_DOWN
        3. If ADX < adx_range_threshold (weak trend):
           - If ATR/close < atr_low_threshold => LOW_VOLATILITY
           - Otherwise => RANGING
        4. Border zone (adx_range <= ADX <= adx_trend):
           - If ATR/close < atr_low_threshold => LOW_VOLATILITY
           - Otherwise => RANGING

        High volatility always takes first priority. Trend strength (ADX)
        drives the main classification. Within non-trending regimes, ATR
        distinguishes low-volatility from ranging.
        """
        self._validate(df)

        close = df["close"]
        high = df["high"]
        low = df["low"]

        # Latest values
        adx_val = float(_adx(high, low, close, self.adx_length).iloc[-1])
        atr_val = float(_atr(high, low, close, self.atr_length).iloc[-1])
        sma_val = float(_sma(close, self.sma_length).iloc[-1])
        last_close = float(close.iloc[-1])

        atr_ratio = atr_val / last_close if last_close > 0 else 0.0

        # 1. Extreme volatility takes highest priority
        if atr_ratio > self.atr_high_threshold:
            return MarketRegime.HIGH_VOLATILITY

        # 2. Strong trend (ADX above trend threshold)
        if adx_val > self.adx_trend_threshold:
            if last_close > sma_val:
                return MarketRegime.TRENDING_UP
            else:
                return MarketRegime.TRENDING_DOWN

        # 3. Weak trend or border zone — distinguish ranging from low-vol
        if atr_ratio < self.atr_low_threshold:
            return MarketRegime.LOW_VOLATILITY

        return MarketRegime.RANGING

    def detect_with_ml(self, df: pd.DataFrame) -> tuple[MarketRegime, float]:
        """ML-based regime detection using Gaussian Mixture Model.

        Features extracted: returns, volatility, volume_ratio, trend_strength.
        Returns (regime, confidence) where confidence is in [0, 1].
        """
        from sklearn.mixture import GaussianMixture

        self._validate(df)

        features = self._extract_features(df)
        if features.shape[0] < 30:
            # Fall back to rule-based if insufficient data for ML
            regime = self.detect(df)
            return regime, 0.5

        n_components = len(MarketRegime)
        gmm = GaussianMixture(
            n_components=n_components,
            covariance_type="full",
            n_init=3,
            random_state=42,
        )
        gmm.fit(features)

        # Predict cluster for the latest observation
        latest = features.iloc[[-1]]
        proba = gmm.predict_proba(latest)[0]
        cluster = int(np.argmax(proba))
        confidence = float(proba[cluster])

        # Map cluster to regime using cluster centroid characteristics
        regime = self._map_cluster_to_regime(gmm, features, cluster)
        return regime, confidence

    # ---- internal helpers ----

    def _validate(self, df: pd.DataFrame) -> None:
        required = {"open", "high", "low", "close", "volume"}
        missing = required - set(df.columns)
        if missing:
            raise ValueError(f"DataFrame missing required columns: {missing}")
        if len(df) < _MIN_BARS:
            raise ValueError(
                f"Need at least {_MIN_BARS} bars for regime detection, got {len(df)}"
            )

    def _extract_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Build feature matrix for ML-based detection."""
        close = df["close"]
        high = df["high"]
        low = df["low"]
        volume = df["volume"]

        returns = close.pct_change()
        volatility = returns.rolling(20).std()
        vol_ma = volume.rolling(20).mean()
        volume_ratio = volume / vol_ma.replace(0, np.nan)
        trend_strength = (close - _sma(close, self.sma_length)) / _sma(close, self.sma_length).replace(0, np.nan)

        features = pd.DataFrame(
            {
                "returns": returns,
                "volatility": volatility,
                "volume_ratio": volume_ratio,
                "trend_strength": trend_strength,
            }
        )
        return features.dropna()

    def _map_cluster_to_regime(
        self,
        gmm: object,
        features: pd.DataFrame,
        cluster: int,
    ) -> MarketRegime:
        """Map a GMM cluster index to a MarketRegime using centroid feature values."""
        labels = gmm.predict(features)  # type: ignore[attr-defined]
        mask = labels == cluster
        if not mask.any():
            return MarketRegime.RANGING

        subset = features.loc[mask]
        mean_return = subset["returns"].mean()
        mean_vol = subset["volatility"].mean()
        mean_trend = subset["trend_strength"].mean()

        # Classify by dominant characteristic
        overall_vol = features["volatility"].mean()
        vol_threshold = 1.5

        if mean_vol > overall_vol * vol_threshold:
            return MarketRegime.HIGH_VOLATILITY
        if mean_vol < overall_vol / vol_threshold:
            return MarketRegime.LOW_VOLATILITY
        if mean_trend > 0.02 and mean_return > 0:
            return MarketRegime.TRENDING_UP
        if mean_trend < -0.02 and mean_return < 0:
            return MarketRegime.TRENDING_DOWN
        return MarketRegime.RANGING
