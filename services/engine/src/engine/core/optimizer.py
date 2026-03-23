import itertools
from dataclasses import dataclass

import pandas as pd

from engine.core.backtest import BacktestEngine, BacktestResult
from engine.strategies.base import AbstractStrategy


@dataclass
class OptimizationResult:
    best_params: dict
    best_metric: float
    all_results: list[tuple[dict, float]]


class ParameterOptimizer:
    """Grid search parameter optimizer for strategies."""

    def __init__(self, engine: BacktestEngine | None = None) -> None:
        self.engine = engine or BacktestEngine()

    def optimize(
        self,
        strategy_cls: type[AbstractStrategy],
        data: pd.DataFrame,
        param_grid: dict[str, list],
        metric: str = "sharpe_ratio",
        maximize: bool = True,
    ) -> OptimizationResult:
        """Run grid search over parameter combinations."""
        keys = list(param_grid.keys())
        values = list(param_grid.values())
        combos = list(itertools.product(*values))

        results: list[tuple[dict, float]] = []
        for combo in combos:
            params = dict(zip(keys, combo))
            strategy = strategy_cls(**params)
            result: BacktestResult = self.engine.run(strategy, data)
            metric_val = result.metrics.get(metric, 0.0)
            results.append((params, metric_val))

        results.sort(key=lambda x: x[1], reverse=maximize)
        best_params, best_metric = results[0]

        return OptimizationResult(
            best_params=best_params,
            best_metric=best_metric,
            all_results=results,
        )
