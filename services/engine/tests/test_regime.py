"""Tests for market regime detection, strategy selection, and adaptive engine."""

import numpy as np
import pandas as pd
import pytest

from engine.core.regime_detector import MarketRegime, RegimeDetector
from engine.core.strategy_selector import StrategySelector
from engine.core.adaptive_engine import AdaptiveEngine


# --------------- Test data generators ---------------


def _make_trending_up(n: int = 120, seed: int = 42) -> pd.DataFrame:
    """Generate strongly trending-up OHLCV data.

    Strong upward drift (+0.5/bar) with small noise => ADX >> 25, close > SMA50.
    Moderate H-L range keeps ATR/close in the normal band (not high-vol, not low-vol).
    """
    rng = np.random.RandomState(seed)
    dates = pd.bdate_range("2024-01-01", periods=n, freq="D")
    close = 100 + np.cumsum(np.full(n, 0.5) + rng.randn(n) * 0.1)
    close = np.maximum(close, 10)
    high = close + rng.uniform(0.2, 0.8, n)
    low = close - rng.uniform(0.2, 0.8, n)
    open_ = close + rng.uniform(-0.3, 0.3, n)
    volume = rng.randint(5000, 15000, n).astype(float)
    return pd.DataFrame(
        {"open": open_, "high": high, "low": low, "close": close, "volume": volume},
        index=dates,
    )


def _make_trending_down(n: int = 120, seed: int = 42) -> pd.DataFrame:
    """Generate strongly trending-down OHLCV data.

    Strong downward drift (-0.5/bar) => ADX >> 25, close < SMA50.
    """
    rng = np.random.RandomState(seed)
    dates = pd.bdate_range("2024-01-01", periods=n, freq="D")
    close = 200 + np.cumsum(np.full(n, -0.5) + rng.randn(n) * 0.1)
    close = np.maximum(close, 10)
    high = close + rng.uniform(0.2, 0.8, n)
    low = close - rng.uniform(0.2, 0.8, n)
    open_ = close + rng.uniform(-0.3, 0.3, n)
    volume = rng.randint(5000, 15000, n).astype(float)
    return pd.DataFrame(
        {"open": open_, "high": high, "low": low, "close": close, "volume": volume},
        index=dates,
    )


def _make_ranging(n: int = 120, seed: int = 42) -> pd.DataFrame:
    """Generate sideways/ranging OHLCV data.

    Mean-reverting close (Ornstein-Uhlenbeck style) around 100 => low ADX.
    Moderate H-L range keeps ATR/close above the low-vol threshold.
    """
    rng = np.random.RandomState(seed)
    dates = pd.bdate_range("2024-01-01", periods=n, freq="D")
    close = np.zeros(n)
    close[0] = 100.0
    for i in range(1, n):
        close[i] = close[i - 1] + rng.randn() * 0.3 - 0.05 * (close[i - 1] - 100)
    close = np.maximum(close, 90)
    high = close + rng.uniform(0.5, 1.5, n)
    low = close - rng.uniform(0.5, 1.5, n)
    low = np.maximum(low, 1)
    open_ = close + rng.uniform(-0.3, 0.3, n)
    volume = rng.randint(5000, 15000, n).astype(float)
    return pd.DataFrame(
        {"open": open_, "high": high, "low": low, "close": close, "volume": volume},
        index=dates,
    )


def _make_high_volatility(n: int = 120, seed: int = 42) -> pd.DataFrame:
    """Generate high-volatility OHLCV data with large swings.

    Large random walk noise + very wide H-L range => ATR/close >> 0.03.
    """
    rng = np.random.RandomState(seed)
    dates = pd.bdate_range("2024-01-01", periods=n, freq="D")
    close = 100 + np.cumsum(rng.randn(n) * 4.0)
    close = np.maximum(close, 10)
    high = close + rng.uniform(3, 8, n)
    low = close - rng.uniform(3, 8, n)
    low = np.maximum(low, 1)
    open_ = close + rng.uniform(-2, 2, n)
    volume = rng.randint(10000, 30000, n).astype(float)
    return pd.DataFrame(
        {"open": open_, "high": high, "low": low, "close": close, "volume": volume},
        index=dates,
    )


def _make_low_volatility(n: int = 120, seed: int = 42) -> pd.DataFrame:
    """Generate low-volatility OHLCV data with very small price changes.

    Tiny random walk + minimal H-L range => ATR/close << 0.01.
    No strong trend, so ADX stays low-to-moderate.
    """
    rng = np.random.RandomState(seed)
    dates = pd.bdate_range("2024-01-01", periods=n, freq="D")
    close = 100 + np.cumsum(rng.randn(n) * 0.02)
    close = np.maximum(close, 90)
    high = close + rng.uniform(0.01, 0.05, n)
    low = close - rng.uniform(0.01, 0.05, n)
    open_ = close + rng.uniform(-0.02, 0.02, n)
    volume = rng.randint(1000, 3000, n).astype(float)
    return pd.DataFrame(
        {"open": open_, "high": high, "low": low, "close": close, "volume": volume},
        index=dates,
    )


# --------------- TestRegimeDetector ---------------


class TestRegimeDetector:
    """Test rule-based regime detection."""

    def test_detects_trending_up(self):
        df = _make_trending_up()
        detector = RegimeDetector()
        regime = detector.detect(df)
        assert regime == MarketRegime.TRENDING_UP

    def test_detects_trending_down(self):
        df = _make_trending_down()
        detector = RegimeDetector()
        regime = detector.detect(df)
        assert regime == MarketRegime.TRENDING_DOWN

    def test_detects_ranging(self):
        df = _make_ranging()
        detector = RegimeDetector()
        regime = detector.detect(df)
        assert regime == MarketRegime.RANGING

    def test_detects_high_volatility(self):
        df = _make_high_volatility()
        detector = RegimeDetector()
        regime = detector.detect(df)
        assert regime == MarketRegime.HIGH_VOLATILITY

    def test_detects_low_volatility(self):
        df = _make_low_volatility()
        detector = RegimeDetector()
        regime = detector.detect(df)
        assert regime == MarketRegime.LOW_VOLATILITY

    def test_insufficient_data_raises(self):
        df = _make_trending_up(n=30)
        detector = RegimeDetector()
        with pytest.raises(ValueError, match="at least 60 bars"):
            detector.detect(df)

    def test_missing_columns_raises(self):
        df = pd.DataFrame({"close": [1, 2, 3]})
        detector = RegimeDetector()
        with pytest.raises(ValueError, match="missing required columns"):
            detector.detect(df)

    def test_custom_thresholds(self):
        df = _make_trending_up()
        # Very high ADX threshold — should push result away from trending
        detector = RegimeDetector(adx_trend_threshold=99.0, adx_range_threshold=98.0)
        regime = detector.detect(df)
        # With impossible ADX threshold, it should fall through to ranging or volatility
        assert regime in list(MarketRegime)

    def test_regime_enum_values(self):
        """All enum values are valid strings."""
        assert MarketRegime.TRENDING_UP.value == "trending_up"
        assert MarketRegime.TRENDING_DOWN.value == "trending_down"
        assert MarketRegime.RANGING.value == "ranging"
        assert MarketRegime.HIGH_VOLATILITY.value == "high_volatility"
        assert MarketRegime.LOW_VOLATILITY.value == "low_volatility"

    def test_detect_with_ml_returns_tuple(self):
        """ML detection returns (regime, confidence)."""
        df = _make_trending_up(n=120)
        detector = RegimeDetector()
        regime, confidence = detector.detect_with_ml(df)
        assert isinstance(regime, MarketRegime)
        assert 0.0 <= confidence <= 1.0

    def test_detect_with_ml_low_data_fallback(self):
        """ML detection falls back to rule-based with low confidence when data is marginal."""
        df = _make_trending_up(n=65)  # Enough for rule-based, marginal for ML
        detector = RegimeDetector()
        regime, confidence = detector.detect_with_ml(df)
        assert isinstance(regime, MarketRegime)
        assert confidence == 0.5  # fallback confidence


# --------------- TestStrategySelector ---------------


class TestStrategySelector:
    """Test strategy selection based on market regime."""

    def test_select_trending_up(self):
        selector = StrategySelector()
        result = selector.select(MarketRegime.TRENDING_UP)
        assert "sma_crossover" in result
        assert "momentum" in result

    def test_select_trending_down(self):
        selector = StrategySelector()
        result = selector.select(MarketRegime.TRENDING_DOWN)
        assert "rsi_mean_reversion" in result

    def test_select_ranging(self):
        selector = StrategySelector()
        result = selector.select(MarketRegime.RANGING)
        assert "rsi_mean_reversion" in result
        assert "bollinger_breakout" in result

    def test_select_high_volatility(self):
        selector = StrategySelector()
        result = selector.select(MarketRegime.HIGH_VOLATILITY)
        assert "bollinger_breakout" in result
        assert "grid_trading" in result

    def test_select_low_volatility(self):
        selector = StrategySelector()
        result = selector.select(MarketRegime.LOW_VOLATILITY)
        assert "pairs_trading" in result
        assert "momentum" in result

    def test_select_filters_by_available(self):
        selector = StrategySelector()
        result = selector.select(
            MarketRegime.TRENDING_UP,
            available_strategies=["sma_crossover", "grid_trading"],
        )
        assert result == ["sma_crossover"]

    def test_select_no_match(self):
        selector = StrategySelector()
        result = selector.select(
            MarketRegime.TRENDING_UP,
            available_strategies=["nonexistent"],
        )
        assert result == []

    def test_select_best(self):
        selector = StrategySelector()
        best = selector.select_best(MarketRegime.TRENDING_UP)
        assert best == "sma_crossover"

    def test_select_best_none(self):
        selector = StrategySelector()
        best = selector.select_best(
            MarketRegime.TRENDING_UP,
            available_strategies=["nonexistent"],
        )
        assert best is None

    def test_custom_mapping(self):
        custom = {MarketRegime.RANGING: ["my_custom_strategy"]}
        selector = StrategySelector(regime_strategy_map=custom)
        result = selector.select(MarketRegime.RANGING)
        assert result == ["my_custom_strategy"]
        # Other regimes should return empty
        assert selector.select(MarketRegime.TRENDING_UP) == []

    def test_preserves_ranking_order(self):
        selector = StrategySelector()
        result = selector.select(MarketRegime.TRENDING_UP)
        assert result == ["sma_crossover", "momentum", "dual_ma"]


# --------------- TestAdaptiveEngine ---------------


class TestAdaptiveEngine:
    """End-to-end tests for the adaptive engine."""

    @pytest.mark.asyncio
    async def test_analyze_and_recommend_trending_up(self):
        df = _make_trending_up()
        engine = AdaptiveEngine()
        result = await engine.analyze_and_recommend("BTC/USDT", df)

        assert result["symbol"] == "BTC/USDT"
        assert result["regime"] == "trending_up"
        assert result["confidence"] == 1.0
        assert isinstance(result["recommended_strategies"], list)
        assert len(result["recommended_strategies"]) > 0
        assert isinstance(result["reason"], str)
        assert len(result["reason"]) > 0

    @pytest.mark.asyncio
    async def test_analyze_and_recommend_ranging(self):
        df = _make_ranging()
        engine = AdaptiveEngine()
        result = await engine.analyze_and_recommend("ETH/USDT", df)

        assert result["regime"] == "ranging"
        assert "rsi_mean_reversion" in result["recommended_strategies"]

    @pytest.mark.asyncio
    async def test_analyze_with_available_strategies(self):
        df = _make_trending_up()
        engine = AdaptiveEngine()
        result = await engine.analyze_and_recommend(
            "BTC/USDT", df, available_strategies=["sma_crossover"]
        )
        assert result["recommended_strategies"] == ["sma_crossover"]

    @pytest.mark.asyncio
    async def test_analyze_with_ml(self):
        df = _make_trending_up(n=120)
        engine = AdaptiveEngine()
        result = await engine.analyze_and_recommend("BTC/USDT", df, use_ml=True)

        assert result["symbol"] == "BTC/USDT"
        assert result["regime"] in [r.value for r in MarketRegime]
        assert 0.0 <= result["confidence"] <= 1.0

    @pytest.mark.asyncio
    async def test_full_analysis(self):
        df = _make_trending_up(n=120)
        engine = AdaptiveEngine()
        result = await engine.full_analysis("BTC/USDT", df)

        assert result["symbol"] == "BTC/USDT"
        assert "rule_based" in result
        assert "ml_based" in result
        assert isinstance(result["consensus"], bool)
        assert result["rule_based"]["regime"] in [r.value for r in MarketRegime]
        assert result["ml_based"]["regime"] in [r.value for r in MarketRegime]

    @pytest.mark.asyncio
    async def test_all_regimes_produce_recommendations(self):
        """Every regime type should produce at least one recommended strategy."""
        datasets = {
            "trending_up": _make_trending_up(),
            "trending_down": _make_trending_down(),
            "ranging": _make_ranging(),
            "high_volatility": _make_high_volatility(),
            "low_volatility": _make_low_volatility(),
        }
        engine = AdaptiveEngine()
        for label, df in datasets.items():
            result = await engine.analyze_and_recommend(f"TEST/{label}", df)
            assert len(result["recommended_strategies"]) > 0, (
                f"No strategies recommended for {label} regime"
            )
