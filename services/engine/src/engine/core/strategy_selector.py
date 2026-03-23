"""Strategy selection based on detected market regime.

Maps each MarketRegime to a ranked list of strategies, and provides
methods to select the best candidate from those available.
"""

from __future__ import annotations

import logging

import pandas as pd

from engine.core.regime_detector import MarketRegime

logger = logging.getLogger(__name__)

# Default mapping: regime -> ordered list of strategy names (best first)
_DEFAULT_REGIME_STRATEGY_MAP: dict[MarketRegime, list[str]] = {
    MarketRegime.TRENDING_UP: [  # 上升趋势 — 顺势策略
        "sma_crossover",
        "momentum",
        "dual_ma",
    ],
    MarketRegime.TRENDING_DOWN: [  # 下降趋势 — 均值回归 / 做空
        "rsi_mean_reversion",
    ],
    MarketRegime.RANGING: [  # 震荡/横盘 — 均值回归 / 网格
        "rsi_mean_reversion",
        "bollinger_breakout",
        "grid_trading",
    ],
    MarketRegime.HIGH_VOLATILITY: [  # 高波动 — 突破 / 网格
        "bollinger_breakout",
        "grid_trading",
    ],
    MarketRegime.LOW_VOLATILITY: [  # 低波动 — 配对 / 动量
        "pairs_trading",
        "momentum",
    ],
}


class StrategySelector:
    """Select the best strategy (or ranked list) for a given market regime."""

    def __init__(
        self,
        regime_strategy_map: dict[MarketRegime, list[str]] | None = None,
    ) -> None:
        self.regime_strategy_map = regime_strategy_map or dict(_DEFAULT_REGIME_STRATEGY_MAP)

    def select(
        self,
        regime: MarketRegime,
        available_strategies: list[str] | None = None,
    ) -> list[str]:
        """Return ranked strategy names for *regime*, filtered to *available_strategies*.

        If *available_strategies* is ``None`` every mapped strategy is returned.
        The original ranking order is preserved.
        """
        candidates = self.regime_strategy_map.get(regime, [])
        if available_strategies is None:
            return list(candidates)
        return [s for s in candidates if s in available_strategies]

    def select_best(
        self,
        regime: MarketRegime,
        available_strategies: list[str] | None = None,
    ) -> str | None:
        """Convenience: return the single top-ranked strategy, or ``None``."""
        ranked = self.select(regime, available_strategies)
        return ranked[0] if ranked else None

    def select_with_backtest(
        self,
        regime: MarketRegime,
        data: pd.DataFrame,
        available_strategies: list[str] | None = None,
        initial_capital: float = 100_000.0,
    ) -> str | None:
        """Back-test all candidate strategies on *data* and return the best performer.

        Uses the engine's ``BacktestEngine`` to run a simple simulation for each
        candidate.  Returns the strategy name with the highest total return, or
        ``None`` if no candidates are available or can be instantiated.
        """
        from engine.core.backtest import BacktestEngine
        from engine.strategies.registry import registry

        candidates = self.select(regime, available_strategies)
        if not candidates:
            return None

        best_name: str | None = None
        best_return: float = float("-inf")

        for name in candidates:
            try:
                strategy = registry.create(name)
            except KeyError:
                logger.debug("Strategy '%s' not in registry, skipping backtest", name)
                continue

            engine = BacktestEngine(initial_capital=initial_capital)
            result = engine.run(strategy, data)
            total_ret = result.metrics.get("total_return", float("-inf"))
            logger.debug("Backtest %s -> total_return=%.4f", name, total_ret)

            if total_ret > best_return:
                best_return = total_ret
                best_name = name

        return best_name
