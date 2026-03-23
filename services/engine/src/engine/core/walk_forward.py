"""Walk-Forward rolling optimization with overfitting detection."""

from __future__ import annotations

import itertools
from dataclasses import dataclass, field

import pandas as pd

from engine.core.backtest import BacktestEngine, BacktestResult
from engine.strategies.base import AbstractStrategy


@dataclass
class WalkForwardWindow:
    """Result for a single walk-forward window."""

    train_start: int  # index into data
    train_end: int
    test_start: int
    test_end: int
    best_params: dict = field(default_factory=dict)
    train_metrics: dict = field(default_factory=dict)
    test_metrics: dict = field(default_factory=dict)


@dataclass
class WalkForwardResult:
    """Aggregated result across all walk-forward windows."""

    windows: list[WalkForwardWindow] = field(default_factory=list)
    overall_test_metrics: dict = field(default_factory=dict)
    overfitting_score: float = 0.0
    is_overfit: bool = False


class WalkForwardOptimizer:
    """Walk-Forward rolling optimizer.

    Splits data into *n_splits* overlapping rolling windows.  For each window
    the optimiser runs a grid search on the training portion, then validates
    the best parameter set on the subsequent test portion.  Finally it
    aggregates test-period performance across all windows and computes an
    overfitting score.

    Parameters
    ----------
    backtest_engine : BacktestEngine
        Engine used to execute each backtest run.
    n_splits : int
        Number of rolling windows (default 5).
    train_pct : float
        Fraction of each window devoted to training (default 0.7).
    overfit_threshold : float
        Overfitting score above which ``is_overfit`` is ``True`` (default 0.5).
    """

    def __init__(
        self,
        backtest_engine: BacktestEngine | None = None,
        n_splits: int = 5,
        train_pct: float = 0.7,
        overfit_threshold: float = 0.5,
    ) -> None:
        self.engine = backtest_engine or BacktestEngine()
        self.n_splits = max(n_splits, 1)
        self.train_pct = min(max(train_pct, 0.1), 0.95)
        self.overfit_threshold = overfit_threshold

    # ------------------------------------------------------------------
    # Window generation
    # ------------------------------------------------------------------

    def _generate_windows(self, n_rows: int) -> list[tuple[int, int, int, int]]:
        """Return list of (train_start, train_end, test_start, test_end).

        Windows are *rolling*: each subsequent window advances by a fixed
        step so that the test portion of one window overlaps with the
        beginning of the next window's training portion.
        """
        # Total span needed per window (train + test)
        window_size = n_rows // self.n_splits
        if window_size < 2:
            raise ValueError(
                f"Not enough data ({n_rows} rows) for {self.n_splits} splits"
            )

        train_size = max(int(window_size * self.train_pct), 1)
        test_size = max(window_size - train_size, 1)

        # Step: advance each window by test_size to keep rolling
        step = test_size

        windows: list[tuple[int, int, int, int]] = []
        for i in range(self.n_splits):
            train_start = i * step
            train_end = train_start + train_size  # exclusive
            test_start = train_end
            test_end = test_start + test_size  # exclusive

            if test_end > n_rows:
                # Trim last window to fit available data
                test_end = n_rows
                if test_start >= test_end:
                    break

            windows.append((train_start, train_end, test_start, test_end))

        if not windows:
            raise ValueError(
                f"Could not create any valid windows from {n_rows} rows"
            )

        return windows

    # ------------------------------------------------------------------
    # Grid search helper
    # ------------------------------------------------------------------

    def _grid_search(
        self,
        strategy_cls: type[AbstractStrategy],
        data: pd.DataFrame,
        param_grid: dict[str, list],
        metric: str,
        maximize: bool,
    ) -> tuple[dict, dict, float]:
        """Run grid search and return (best_params, best_metrics, best_value)."""
        keys = list(param_grid.keys())
        values = list(param_grid.values())
        combos = list(itertools.product(*values))

        best_params: dict = {}
        best_metrics: dict = {}
        best_val: float | None = None

        for combo in combos:
            params = dict(zip(keys, combo))
            strategy = strategy_cls(**params)
            result: BacktestResult = self.engine.run(strategy, data)
            val = result.metrics.get(metric, 0.0)

            if best_val is None or (maximize and val > best_val) or (not maximize and val < best_val):
                best_val = val
                best_params = params
                best_metrics = dict(result.metrics)

        return best_params, best_metrics, best_val if best_val is not None else 0.0

    # ------------------------------------------------------------------
    # Overfitting score
    # ------------------------------------------------------------------

    @staticmethod
    def _compute_overfitting_score(
        train_values: list[float],
        test_values: list[float],
    ) -> float:
        """Compute overfitting score in [0, 1].

        ``score = 1 - (avg_test / avg_train)``

        Special cases:
        * If both averages are zero the score is 0 (no information).
        * If avg_train is zero but avg_test is not the score is clamped to 0
          (we cannot divide but there is no evidence of overfitting).
        * Negative avg_train is handled by taking the absolute ratio – if
          test degrades relative to train the score will be high.
        * The result is clamped to [0, 1].
        """
        n = len(train_values)
        if n == 0:
            return 0.0

        avg_train = sum(train_values) / n
        avg_test = sum(test_values) / n

        if avg_train == 0.0:
            return 0.0 if avg_test == 0.0 else 0.0

        # Use absolute value of avg_train for sign-safe division
        ratio = avg_test / avg_train
        # When both are negative, ratio is positive – that is fine.
        # When signs differ, ratio is negative – strong overfitting.

        score = 1.0 - ratio
        return max(0.0, min(score, 1.0))

    # ------------------------------------------------------------------
    # Main entry point
    # ------------------------------------------------------------------

    def optimize(
        self,
        strategy_cls: type[AbstractStrategy],
        data: pd.DataFrame,
        param_grid: dict[str, list],
        metric: str = "sharpe_ratio",
        maximize: bool = True,
    ) -> WalkForwardResult:
        """Run walk-forward optimisation.

        1. Split *data* into *n_splits* rolling windows.
        2. For each window run grid search on the training portion.
        3. Validate the winning parameters on the test portion.
        4. Aggregate test metrics and compute the overfitting score.
        """
        n_rows = len(data)
        raw_windows = self._generate_windows(n_rows)

        windows: list[WalkForwardWindow] = []
        train_metric_vals: list[float] = []
        test_metric_vals: list[float] = []

        # Accumulate per-metric sums for overall_test_metrics
        test_metric_sums: dict[str, float] = {}
        test_metric_counts: int = 0

        for train_start, train_end, test_start, test_end in raw_windows:
            train_data = data.iloc[train_start:train_end]
            test_data = data.iloc[test_start:test_end]

            # Step 1: find best params on training set
            best_params, train_metrics, train_val = self._grid_search(
                strategy_cls, train_data, param_grid, metric, maximize
            )

            # Step 2: validate on test set
            strategy = strategy_cls(**best_params)
            test_result: BacktestResult = self.engine.run(strategy, test_data)
            test_metrics = dict(test_result.metrics)
            test_val = test_metrics.get(metric, 0.0)

            train_metric_vals.append(train_val)
            test_metric_vals.append(test_val)

            # Accumulate for overall averages
            for k, v in test_metrics.items():
                test_metric_sums[k] = test_metric_sums.get(k, 0.0) + v
            test_metric_counts += 1

            windows.append(
                WalkForwardWindow(
                    train_start=train_start,
                    train_end=train_end,
                    test_start=test_start,
                    test_end=test_end,
                    best_params=best_params,
                    train_metrics=train_metrics,
                    test_metrics=test_metrics,
                )
            )

        # Overall test metrics: average across all windows
        overall_test_metrics: dict[str, float] = {}
        if test_metric_counts > 0:
            for k, v in test_metric_sums.items():
                overall_test_metrics[k] = round(v / test_metric_counts, 4)

        # Overfitting score
        overfitting_score = self._compute_overfitting_score(
            train_metric_vals, test_metric_vals
        )
        is_overfit = overfitting_score > self.overfit_threshold

        return WalkForwardResult(
            windows=windows,
            overall_test_metrics=overall_test_metrics,
            overfitting_score=round(overfitting_score, 4),
            is_overfit=is_overfit,
        )
