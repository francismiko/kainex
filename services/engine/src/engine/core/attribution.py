"""Trade attribution analysis.

Decomposes each trade's PnL into contributing factors (signal type,
market regime, entry/exit timing, costs) so users can understand
*when* and *why* a strategy succeeds or fails.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass

import numpy as np
import pandas as pd

from engine.core.regime_detector import MarketRegime, RegimeDetector

logger = logging.getLogger(__name__)

# --------------- Constants ---------------

# Number of bars after entry/before exit used to evaluate timing quality.
_TIMING_WINDOW = 5

# Threshold (fractional) for classifying timing as good / bad.
_TIMING_GOOD_PCT = 0.01  # > 1 %
_TIMING_BAD_PCT = -0.01  # < -1 %


# --------------- Data classes ---------------


@dataclass
class TradeAttribution:
    """Attribution result for a single trade."""

    trade_id: str
    symbol: str
    pnl: float
    # Attribution factors
    signal_type: str  # "sma_crossover", "rsi_oversold", etc.
    market_regime: str  # MarketRegime value at entry
    entry_timing: str  # "good" / "neutral" / "bad"
    exit_timing: str  # "good" / "neutral" / "bad"
    holding_period_hours: float
    slippage_cost: float
    commission_cost: float


# --------------- Analyzer ---------------


class AttributionAnalyzer:
    """Analyze trades and attribute PnL to specific factors.

    Parameters
    ----------
    regime_detector:
        A :class:`RegimeDetector` used to classify the market state at
        entry time for each trade.
    timing_window:
        Number of bars after entry / before exit to evaluate timing.
    timing_good_pct:
        Price movement threshold (fraction) above which timing is "good".
    timing_bad_pct:
        Price movement threshold (fraction) below which timing is "bad".
    """

    def __init__(
        self,
        regime_detector: RegimeDetector,
        timing_window: int = _TIMING_WINDOW,
        timing_good_pct: float = _TIMING_GOOD_PCT,
        timing_bad_pct: float = _TIMING_BAD_PCT,
    ) -> None:
        self.regime_detector = regime_detector
        self.timing_window = timing_window
        self.timing_good_pct = timing_good_pct
        self.timing_bad_pct = timing_bad_pct

    # ---- public API ----

    def analyze_trades(
        self,
        trades: list[dict],
        data: pd.DataFrame,
    ) -> list[TradeAttribution]:
        """Attribute every trade in *trades* using *data* (OHLCV DataFrame).

        Each element of *trades* is expected to have at minimum:
            - entry_time  (datetime-like, must exist in ``data.index``)
            - exit_time   (datetime-like or ``None`` for open trades)
            - entry_price (float)
            - exit_price  (float or ``None``)
            - pnl         (float)
            - symbol      (str)

        Optional keys:
            - signal_type     (str) — strategy signal name; defaults to ``"unknown"``
            - slippage_cost   (float) — estimated slippage; defaults to 0.0
            - commission_cost (float) — estimated commission; defaults to 0.0
        """
        results: list[TradeAttribution] = []

        for idx, trade in enumerate(trades):
            attr = self._analyze_single(trade, data, idx)
            results.append(attr)

        return results

    def summarize(self, attributions: list[TradeAttribution]) -> dict:
        """Aggregate attribution results into a front-end-friendly summary."""
        if not attributions:
            return self._empty_summary()

        by_regime: dict[str, list[TradeAttribution]] = {}
        by_signal: dict[str, list[TradeAttribution]] = {}
        entry_timing_counts = {"good": 0, "neutral": 0, "bad": 0}
        exit_timing_counts = {"good": 0, "neutral": 0, "bad": 0}
        total_slippage = 0.0
        total_commission = 0.0
        total_abs_pnl = 0.0

        for a in attributions:
            by_regime.setdefault(a.market_regime, []).append(a)
            by_signal.setdefault(a.signal_type, []).append(a)
            entry_timing_counts[a.entry_timing] += 1
            exit_timing_counts[a.exit_timing] += 1
            total_slippage += a.slippage_cost
            total_commission += a.commission_cost
            total_abs_pnl += abs(a.pnl)

        regime_summary = {}
        for regime, group in by_regime.items():
            pnls = [t.pnl for t in group]
            wins = sum(1 for p in pnls if p > 0)
            regime_summary[regime] = {
                "count": len(group),
                "win_rate": round(wins / len(group), 4) if group else 0.0,
                "avg_pnl": round(float(np.mean(pnls)), 4),
            }

        signal_summary = {}
        for signal, group in by_signal.items():
            pnls = [t.pnl for t in group]
            wins = sum(1 for p in pnls if p > 0)
            signal_summary[signal] = {
                "count": len(group),
                "win_rate": round(wins / len(group), 4) if group else 0.0,
            }

        cost_as_pct = (
            round((total_slippage + total_commission) / total_abs_pnl, 4)
            if total_abs_pnl > 0
            else 0.0
        )

        return {
            "by_regime": regime_summary,
            "by_signal": signal_summary,
            "timing_quality": {
                "entry": entry_timing_counts,
                "exit": exit_timing_counts,
            },
            "cost_analysis": {
                "total_slippage": round(total_slippage, 4),
                "total_commission": round(total_commission, 4),
                "cost_as_pct_of_pnl": cost_as_pct,
            },
        }

    # ---- internals ----

    def _analyze_single(
        self,
        trade: dict,
        data: pd.DataFrame,
        index: int,
    ) -> TradeAttribution:
        trade_id = trade.get("trade_id", str(index))
        symbol = trade.get("symbol", "UNKNOWN")
        pnl = float(trade.get("pnl", 0.0))
        signal_type = trade.get("signal_type", "unknown")
        slippage_cost = float(trade.get("slippage_cost", 0.0))
        commission_cost = float(trade.get("commission_cost", 0.0))

        entry_time = trade.get("entry_time")
        exit_time = trade.get("exit_time")
        entry_price = float(trade.get("entry_price", 0.0))

        # 1. Market regime at entry
        market_regime = self._detect_regime_at(data, entry_time)

        # 2. Entry timing
        entry_timing = self._evaluate_entry_timing(
            data, entry_time, entry_price, trade.get("side", "buy"),
        )

        # 3. Exit timing
        exit_timing = self._evaluate_exit_timing(
            data, exit_time, float(trade.get("exit_price", 0.0)), trade.get("side", "buy"),
        )

        # 4. Holding period
        holding_period_hours = self._holding_hours(entry_time, exit_time)

        return TradeAttribution(
            trade_id=trade_id,
            symbol=symbol,
            pnl=pnl,
            signal_type=signal_type,
            market_regime=market_regime,
            entry_timing=entry_timing,
            exit_timing=exit_timing,
            holding_period_hours=holding_period_hours,
            slippage_cost=slippage_cost,
            commission_cost=commission_cost,
        )

    # -- regime detection at a point in time --

    def _detect_regime_at(self, data: pd.DataFrame, timestamp) -> str:
        """Detect the market regime using data up to *timestamp*.

        Falls back to ``"unknown"`` when there is insufficient data.
        """
        if timestamp is None:
            return "unknown"

        ts = pd.Timestamp(timestamp)
        # Strip timezone if the index is tz-naive
        if data.index.tz is None and ts.tzinfo is not None:
            ts = ts.tz_localize(None)

        subset = data.loc[data.index <= ts]
        if len(subset) < 60:
            return "unknown"

        try:
            regime = self.regime_detector.detect(subset)
            return regime.value
        except (ValueError, Exception) as exc:  # noqa: BLE001
            logger.debug("Regime detection failed at %s: %s", timestamp, exc)
            return "unknown"

    # -- timing evaluation helpers --

    def _evaluate_entry_timing(
        self,
        data: pd.DataFrame,
        entry_time,
        entry_price: float,
        side: str,
    ) -> str:
        """Evaluate entry timing by looking at price movement over the next N bars.

        For a *buy*:
            - price goes up > timing_good_pct  => "good"
            - price goes down < timing_bad_pct => "bad"
            - otherwise                        => "neutral"
        """
        if entry_time is None or entry_price <= 0:
            return "neutral"

        future_prices = self._future_closes(data, entry_time, self.timing_window)
        if future_prices is None or len(future_prices) == 0:
            return "neutral"

        max_future = float(future_prices.max())
        min_future = float(future_prices.min())

        if side == "buy":
            best_move = (max_future - entry_price) / entry_price
            worst_move = (min_future - entry_price) / entry_price
        else:  # sell / short
            best_move = (entry_price - min_future) / entry_price
            worst_move = (entry_price - max_future) / entry_price

        # Classify by the dominant move
        if best_move > self.timing_good_pct:
            return "good"
        if worst_move < self.timing_bad_pct:
            return "bad"
        return "neutral"

    def _evaluate_exit_timing(
        self,
        data: pd.DataFrame,
        exit_time,
        exit_price: float,
        side: str,
    ) -> str:
        """Evaluate exit timing by checking whether the exit captured a local extremum.

        For a *buy* (long) trade, a good exit means the price *drops* after exit.
        """
        if exit_time is None or exit_price <= 0:
            return "neutral"

        future_prices = self._future_closes(data, exit_time, self.timing_window)
        if future_prices is None or len(future_prices) == 0:
            return "neutral"

        max_future = float(future_prices.max())
        min_future = float(future_prices.min())

        if side == "buy":
            # Exited a long: good if price dropped afterwards
            move = (min_future - exit_price) / exit_price
            if move < self.timing_bad_pct:
                return "good"  # price fell, so we got out at a good time
            upside_left = (max_future - exit_price) / exit_price
            if upside_left > self.timing_good_pct:
                return "bad"  # left money on the table
        else:
            move = (max_future - exit_price) / exit_price
            if move > self.timing_good_pct:
                return "good"
            downside_left = (exit_price - min_future) / exit_price
            if downside_left > self.timing_good_pct:
                return "bad"

        return "neutral"

    # -- utilities --

    def _future_closes(
        self, data: pd.DataFrame, timestamp, n_bars: int
    ) -> pd.Series | None:
        """Return up to *n_bars* close prices strictly after *timestamp*."""
        ts = pd.Timestamp(timestamp)
        if data.index.tz is None and ts.tzinfo is not None:
            ts = ts.tz_localize(None)

        after = data.loc[data.index > ts]
        if after.empty:
            return None
        return after["close"].iloc[:n_bars]

    @staticmethod
    def _holding_hours(entry_time, exit_time) -> float:
        if entry_time is None or exit_time is None:
            return 0.0
        try:
            delta = pd.Timestamp(exit_time) - pd.Timestamp(entry_time)
            return round(delta.total_seconds() / 3600.0, 2)
        except Exception:  # noqa: BLE001
            return 0.0

    @staticmethod
    def _empty_summary() -> dict:
        return {
            "by_regime": {},
            "by_signal": {},
            "timing_quality": {
                "entry": {"good": 0, "neutral": 0, "bad": 0},
                "exit": {"good": 0, "neutral": 0, "bad": 0},
            },
            "cost_analysis": {
                "total_slippage": 0.0,
                "total_commission": 0.0,
                "cost_as_pct_of_pnl": 0.0,
            },
        }
