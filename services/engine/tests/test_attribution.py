"""Tests for trade attribution analysis."""

import numpy as np
import pandas as pd
import pytest

from engine.core.attribution import AttributionAnalyzer, TradeAttribution
from engine.core.regime_detector import MarketRegime, RegimeDetector


# --------------- Test data generators ---------------


def _make_trending_up(n: int = 120, seed: int = 42) -> pd.DataFrame:
    """Generate strongly trending-up OHLCV data."""
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


def _make_ranging(n: int = 120, seed: int = 42) -> pd.DataFrame:
    """Generate sideways/ranging OHLCV data."""
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
    """Generate high-volatility OHLCV data with large swings."""
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


def _sample_trades(data: pd.DataFrame, n_trades: int = 3) -> list[dict]:
    """Generate sample trades spaced across the data."""
    trades = []
    step = max(1, (len(data) - 70) // (n_trades + 1))
    for i in range(n_trades):
        entry_idx = 65 + i * step
        exit_idx = min(entry_idx + 5, len(data) - 2)
        entry_time = data.index[entry_idx]
        exit_time = data.index[exit_idx]
        entry_price = float(data["close"].iloc[entry_idx])
        exit_price = float(data["close"].iloc[exit_idx])
        pnl = (exit_price - entry_price) * 10.0
        trades.append(
            {
                "trade_id": f"trade_{i}",
                "symbol": "BTC/USDT",
                "side": "buy",
                "entry_time": entry_time,
                "exit_time": exit_time,
                "entry_price": entry_price,
                "exit_price": exit_price,
                "pnl": pnl,
                "signal_type": "sma_crossover",
                "slippage_cost": 0.5,
                "commission_cost": 1.0,
            }
        )
    return trades


# --------------- TestAttributionAnalyzer ---------------


class TestAttributionAnalyzer:
    """Test the core AttributionAnalyzer."""

    def test_analyze_trades_returns_list(self):
        data = _make_trending_up()
        trades = _sample_trades(data)
        detector = RegimeDetector()
        analyzer = AttributionAnalyzer(regime_detector=detector)

        result = analyzer.analyze_trades(trades, data)

        assert isinstance(result, list)
        assert len(result) == len(trades)
        for attr in result:
            assert isinstance(attr, TradeAttribution)

    def test_attribution_fields_populated(self):
        data = _make_trending_up()
        trades = _sample_trades(data, n_trades=1)
        detector = RegimeDetector()
        analyzer = AttributionAnalyzer(regime_detector=detector)

        result = analyzer.analyze_trades(trades, data)
        attr = result[0]

        assert attr.trade_id == "trade_0"
        assert attr.symbol == "BTC/USDT"
        assert attr.signal_type == "sma_crossover"
        assert attr.market_regime in [r.value for r in MarketRegime] + ["unknown"]
        assert attr.entry_timing in ("good", "neutral", "bad")
        assert attr.exit_timing in ("good", "neutral", "bad")
        assert attr.holding_period_hours > 0
        assert attr.slippage_cost == 0.5
        assert attr.commission_cost == 1.0

    def test_empty_trades(self):
        data = _make_trending_up()
        detector = RegimeDetector()
        analyzer = AttributionAnalyzer(regime_detector=detector)

        result = analyzer.analyze_trades([], data)
        assert result == []

    def test_missing_optional_fields(self):
        """Trades with minimal fields should not crash."""
        data = _make_trending_up()
        trades = [
            {
                "entry_time": data.index[70],
                "exit_time": data.index[75],
                "entry_price": float(data["close"].iloc[70]),
                "exit_price": float(data["close"].iloc[75]),
                "pnl": 10.0,
            }
        ]
        detector = RegimeDetector()
        analyzer = AttributionAnalyzer(regime_detector=detector)

        result = analyzer.analyze_trades(trades, data)
        assert len(result) == 1
        assert result[0].signal_type == "unknown"
        assert result[0].symbol == "UNKNOWN"

    def test_open_trade_no_exit(self):
        """Trade without exit_time should still work."""
        data = _make_trending_up()
        trades = [
            {
                "trade_id": "open_1",
                "symbol": "ETH/USDT",
                "side": "buy",
                "entry_time": data.index[70],
                "exit_time": None,
                "entry_price": float(data["close"].iloc[70]),
                "exit_price": 0.0,
                "pnl": 0.0,
                "signal_type": "rsi_oversold",
            }
        ]
        detector = RegimeDetector()
        analyzer = AttributionAnalyzer(regime_detector=detector)

        result = analyzer.analyze_trades(trades, data)
        assert len(result) == 1
        assert result[0].exit_timing == "neutral"
        assert result[0].holding_period_hours == 0.0


# --------------- Test regime attribution ---------------


class TestRegimeAttribution:
    """Test attribution under different market regimes."""

    def test_trending_up_regime_detected(self):
        data = _make_trending_up()
        trades = _sample_trades(data, n_trades=2)
        detector = RegimeDetector()
        analyzer = AttributionAnalyzer(regime_detector=detector)

        result = analyzer.analyze_trades(trades, data)
        # In a trending-up dataset, entry at bar 65+ should see trending_up
        regimes = [a.market_regime for a in result]
        assert any(r == "trending_up" for r in regimes)

    def test_ranging_regime_detected(self):
        data = _make_ranging()
        trades = _sample_trades(data, n_trades=2)
        detector = RegimeDetector()
        analyzer = AttributionAnalyzer(regime_detector=detector)

        result = analyzer.analyze_trades(trades, data)
        regimes = [a.market_regime for a in result]
        # In ranging data, at least one trade should be classified as ranging
        assert any(r == "ranging" for r in regimes)

    def test_high_volatility_regime_detected(self):
        data = _make_high_volatility()
        trades = _sample_trades(data, n_trades=2)
        detector = RegimeDetector()
        analyzer = AttributionAnalyzer(regime_detector=detector)

        result = analyzer.analyze_trades(trades, data)
        regimes = [a.market_regime for a in result]
        assert any(r == "high_volatility" for r in regimes)

    def test_early_trade_unknown_regime(self):
        """Trade at the very start of data (< 60 bars) gets 'unknown' regime."""
        data = _make_trending_up()
        trades = [
            {
                "trade_id": "early_0",
                "symbol": "BTC/USDT",
                "side": "buy",
                "entry_time": data.index[10],
                "exit_time": data.index[15],
                "entry_price": float(data["close"].iloc[10]),
                "exit_price": float(data["close"].iloc[15]),
                "pnl": 5.0,
                "signal_type": "sma_crossover",
            }
        ]
        detector = RegimeDetector()
        analyzer = AttributionAnalyzer(regime_detector=detector)

        result = analyzer.analyze_trades(trades, data)
        assert result[0].market_regime == "unknown"


# --------------- TestSummarize ---------------


class TestSummarize:
    """Test the summarize method."""

    def test_summarize_structure(self):
        data = _make_trending_up()
        trades = _sample_trades(data, n_trades=4)
        detector = RegimeDetector()
        analyzer = AttributionAnalyzer(regime_detector=detector)

        attrs = analyzer.analyze_trades(trades, data)
        summary = analyzer.summarize(attrs)

        assert "by_regime" in summary
        assert "by_signal" in summary
        assert "timing_quality" in summary
        assert "cost_analysis" in summary

    def test_summarize_by_regime(self):
        data = _make_trending_up()
        trades = _sample_trades(data, n_trades=3)
        detector = RegimeDetector()
        analyzer = AttributionAnalyzer(regime_detector=detector)

        attrs = analyzer.analyze_trades(trades, data)
        summary = analyzer.summarize(attrs)

        for regime, stats in summary["by_regime"].items():
            assert "count" in stats
            assert "win_rate" in stats
            assert "avg_pnl" in stats
            assert stats["count"] > 0
            assert 0.0 <= stats["win_rate"] <= 1.0

    def test_summarize_by_signal(self):
        data = _make_trending_up()
        trades = _sample_trades(data, n_trades=3)
        # Mix signal types
        trades[0]["signal_type"] = "sma_crossover"
        trades[1]["signal_type"] = "rsi_oversold"
        trades[2]["signal_type"] = "sma_crossover"
        detector = RegimeDetector()
        analyzer = AttributionAnalyzer(regime_detector=detector)

        attrs = analyzer.analyze_trades(trades, data)
        summary = analyzer.summarize(attrs)

        assert "sma_crossover" in summary["by_signal"]
        assert "rsi_oversold" in summary["by_signal"]
        assert summary["by_signal"]["sma_crossover"]["count"] == 2
        assert summary["by_signal"]["rsi_oversold"]["count"] == 1

    def test_summarize_timing_quality(self):
        data = _make_trending_up()
        trades = _sample_trades(data, n_trades=3)
        detector = RegimeDetector()
        analyzer = AttributionAnalyzer(regime_detector=detector)

        attrs = analyzer.analyze_trades(trades, data)
        summary = analyzer.summarize(attrs)

        tq = summary["timing_quality"]
        assert set(tq["entry"].keys()) == {"good", "neutral", "bad"}
        assert set(tq["exit"].keys()) == {"good", "neutral", "bad"}
        total_entry = tq["entry"]["good"] + tq["entry"]["neutral"] + tq["entry"]["bad"]
        assert total_entry == len(trades)

    def test_summarize_cost_analysis(self):
        data = _make_trending_up()
        trades = _sample_trades(data, n_trades=2)
        detector = RegimeDetector()
        analyzer = AttributionAnalyzer(regime_detector=detector)

        attrs = analyzer.analyze_trades(trades, data)
        summary = analyzer.summarize(attrs)

        ca = summary["cost_analysis"]
        assert ca["total_slippage"] == 1.0  # 0.5 * 2
        assert ca["total_commission"] == 2.0  # 1.0 * 2
        assert ca["cost_as_pct_of_pnl"] >= 0.0

    def test_summarize_empty(self):
        detector = RegimeDetector()
        analyzer = AttributionAnalyzer(regime_detector=detector)

        summary = analyzer.summarize([])
        assert summary["by_regime"] == {}
        assert summary["by_signal"] == {}
        assert summary["timing_quality"]["entry"]["good"] == 0
        assert summary["cost_analysis"]["total_slippage"] == 0.0


# --------------- TestTimingEvaluation ---------------


class TestTimingEvaluation:
    """Test entry/exit timing classification."""

    def test_good_entry_timing_in_uptrend(self):
        """Buying early in a strong uptrend should be rated 'good'."""
        data = _make_trending_up(n=120)
        entry_idx = 70
        exit_idx = 80
        entry_price = float(data["close"].iloc[entry_idx])
        exit_price = float(data["close"].iloc[exit_idx])
        trades = [
            {
                "trade_id": "t1",
                "symbol": "BTC/USDT",
                "side": "buy",
                "entry_time": data.index[entry_idx],
                "exit_time": data.index[exit_idx],
                "entry_price": entry_price,
                "exit_price": exit_price,
                "pnl": (exit_price - entry_price) * 10,
                "signal_type": "sma_crossover",
            }
        ]
        detector = RegimeDetector()
        analyzer = AttributionAnalyzer(regime_detector=detector)

        result = analyzer.analyze_trades(trades, data)
        # In a strong uptrend, buying should be classified as "good" entry
        assert result[0].entry_timing == "good"

    def test_custom_timing_thresholds(self):
        """Using extreme thresholds should shift classification."""
        data = _make_trending_up(n=120)
        trades = _sample_trades(data, n_trades=1)
        detector = RegimeDetector()
        # Very high threshold: almost nothing qualifies as "good"
        analyzer = AttributionAnalyzer(
            regime_detector=detector,
            timing_good_pct=0.50,  # 50 % move required
            timing_bad_pct=-0.50,
        )

        result = analyzer.analyze_trades(trades, data)
        assert result[0].entry_timing == "neutral"

    def test_holding_period_calculation(self):
        data = _make_trending_up(n=120)
        entry_time = data.index[70]
        exit_time = data.index[75]
        trades = [
            {
                "trade_id": "hp1",
                "symbol": "BTC/USDT",
                "side": "buy",
                "entry_time": entry_time,
                "exit_time": exit_time,
                "entry_price": 100.0,
                "exit_price": 105.0,
                "pnl": 50.0,
            }
        ]
        detector = RegimeDetector()
        analyzer = AttributionAnalyzer(regime_detector=detector)

        result = analyzer.analyze_trades(trades, data)
        # 5 business days apart = roughly 5 * 24 = 120 hours
        # (exact value depends on bdate_range gaps)
        assert result[0].holding_period_hours > 0
