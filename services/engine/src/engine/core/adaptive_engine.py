"""Adaptive strategy engine: detect regime -> select strategy -> recommend.

Orchestrates ``RegimeDetector`` and ``StrategySelector`` to provide a single
high-level API for market analysis and strategy recommendation.
"""

from __future__ import annotations

import logging

import pandas as pd

from engine.core.regime_detector import MarketRegime, RegimeDetector
from engine.core.strategy_selector import StrategySelector

logger = logging.getLogger(__name__)

# Human-readable regime descriptions (中英双语)
_REGIME_DESCRIPTIONS: dict[MarketRegime, str] = {
    MarketRegime.TRENDING_UP: "市场处于上升趋势状态，推荐使用趋势跟踪策略 (Trending up — use trend-following strategies)",
    MarketRegime.TRENDING_DOWN: "市场处于下降趋势状态，推荐使用均值回归策略 (Trending down — use mean-reversion strategies)",
    MarketRegime.RANGING: "市场处于震荡横盘状态，推荐使用区间交易策略 (Ranging — use range-bound strategies)",
    MarketRegime.HIGH_VOLATILITY: "市场处于高波动状态，推荐使用突破或网格策略 (High volatility — use breakout/grid strategies)",
    MarketRegime.LOW_VOLATILITY: "市场处于低波动状态，推荐使用配对交易或动量策略 (Low volatility — use pairs/momentum strategies)",
}


class AdaptiveEngine:
    """Adaptive strategy engine: detect regime, select strategy, explain reasoning."""

    def __init__(
        self,
        detector: RegimeDetector | None = None,
        selector: StrategySelector | None = None,
    ) -> None:
        self.detector = detector or RegimeDetector()
        self.selector = selector or StrategySelector()

    async def analyze_and_recommend(
        self,
        symbol: str,
        data: pd.DataFrame,
        available_strategies: list[str] | None = None,
        use_ml: bool = False,
    ) -> dict:
        """Analyse *data* for *symbol* and return regime + recommended strategies.

        Returns a dict with keys:
          - symbol: the queried symbol
          - regime: detected MarketRegime value
          - confidence: float in [0, 1] (1.0 for rule-based)
          - recommended_strategies: ranked list[str]
          - reason: human-readable explanation (中英双语)
        """
        if use_ml:
            regime, confidence = self.detector.detect_with_ml(data)
        else:
            regime = self.detector.detect(data)
            confidence = 1.0  # rule-based is deterministic

        strategies = self.selector.select(regime, available_strategies)
        reason = _REGIME_DESCRIPTIONS.get(regime, "")

        result = {
            "symbol": symbol,
            "regime": regime.value,
            "confidence": round(confidence, 4),
            "recommended_strategies": strategies,
            "reason": reason,
        }
        logger.info(
            "Adaptive analysis for %s: regime=%s confidence=%.2f strategies=%s",
            symbol,
            regime.value,
            confidence,
            strategies,
        )
        return result

    async def full_analysis(
        self,
        symbol: str,
        data: pd.DataFrame,
        available_strategies: list[str] | None = None,
    ) -> dict:
        """Run both rule-based and ML detection and return a combined report."""
        rule_regime = self.detector.detect(data)
        rule_strategies = self.selector.select(rule_regime, available_strategies)

        try:
            ml_regime, ml_confidence = self.detector.detect_with_ml(data)
            ml_strategies = self.selector.select(ml_regime, available_strategies)
        except Exception as exc:
            logger.warning("ML detection failed for %s: %s", symbol, exc)
            ml_regime = rule_regime
            ml_confidence = 0.0
            ml_strategies = rule_strategies

        return {
            "symbol": symbol,
            "rule_based": {
                "regime": rule_regime.value,
                "confidence": 1.0,
                "recommended_strategies": rule_strategies,
                "reason": _REGIME_DESCRIPTIONS.get(rule_regime, ""),
            },
            "ml_based": {
                "regime": ml_regime.value,
                "confidence": round(ml_confidence, 4),
                "recommended_strategies": ml_strategies,
                "reason": _REGIME_DESCRIPTIONS.get(ml_regime, ""),
            },
            "consensus": rule_regime.value == ml_regime.value,
        }
