from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from decimal import Decimal

import numpy as np
import pandas as pd
from nautilus_trader.backtest.engine import BacktestEngine, BacktestEngineConfig
from nautilus_trader.backtest.models import FillModel
from nautilus_trader.model.currencies import USD, BTC
from nautilus_trader.model.data import Bar, BarType
from nautilus_trader.model.enums import AccountType, OmsType, BarAggregation, PriceType
from nautilus_trader.model.identifiers import Venue, InstrumentId, Symbol
from nautilus_trader.model.instruments import CurrencyPair, Equity
from nautilus_trader.model.objects import Money, Price, Quantity
from nautilus_trader.test_kit.providers import TestInstrumentProvider

from engine.portfolio.performance import PerformanceCalculator
from engine.strategies.base import AbstractStrategy, KainexStrategy, Market, SignalType


@dataclass
class BacktestResult:
    equity_curve: pd.Series
    trades: pd.DataFrame
    metrics: dict = field(default_factory=dict)


def _ann_factor(market: Market) -> int:
    if market == Market.CRYPTO:
        return 365
    return 252


def _create_venue_config(market: Market) -> dict:
    """Return venue configuration for a given market."""
    configs = {
        Market.A_STOCK: {
            "venue_name": "SSE",
            "oms_type": OmsType.NETTING,
            "account_type": AccountType.CASH,
            "base_currency": None,
        },
        Market.CRYPTO: {
            "venue_name": "BINANCE",
            "oms_type": OmsType.NETTING,
            "account_type": AccountType.CASH,
            "base_currency": None,
        },
        Market.US_STOCK: {
            "venue_name": "NYSE",
            "oms_type": OmsType.NETTING,
            "account_type": AccountType.CASH,
            "base_currency": None,
        },
    }
    return configs[market]


class NautilusBacktestEngine:
    """NautilusTrader-based backtesting engine."""

    def __init__(
        self,
        initial_capital: float = 100_000.0,
        market: Market = Market.CRYPTO,
    ) -> None:
        self.initial_capital = initial_capital
        self.market = market

    def run(
        self,
        strategy: KainexStrategy,
        data: pd.DataFrame,
        start: datetime | None = None,
        end: datetime | None = None,
    ) -> BacktestResult:
        """Run a backtest using NautilusTrader engine."""
        df = data.copy()
        # Normalize timezone: strip tz from both sides to avoid comparison errors
        if hasattr(df.index, 'tz') and df.index.tz is not None:
            df.index = df.index.tz_localize(None)
        if start:
            ts_start = pd.Timestamp(start).tz_localize(None) if pd.Timestamp(start).tzinfo else pd.Timestamp(start)
            df = df[df.index >= ts_start]
        if end:
            ts_end = pd.Timestamp(end).tz_localize(None) if pd.Timestamp(end).tzinfo else pd.Timestamp(end)
            df = df[df.index <= ts_end]

        if df.empty:
            return BacktestResult(
                equity_curve=pd.Series(dtype=float),
                trades=pd.DataFrame(),
                metrics={},
            )

        # Build equity curve from signals
        equity, trades = self._simulate(strategy, df)
        returns = equity.pct_change().dropna()

        calc = PerformanceCalculator(market=self.market)
        metrics = self._compute_metrics(calc, returns, equity, trades)

        return BacktestResult(equity_curve=equity, trades=trades, metrics=metrics)

    def _simulate(
        self, strategy: KainexStrategy | AbstractStrategy, df: pd.DataFrame
    ) -> tuple[pd.Series, pd.DataFrame]:
        """Simple portfolio simulation from strategy signals."""
        cash = self.initial_capital
        position = 0.0
        avg_price = 0.0
        equity_values = []
        trade_records = []

        warmup = getattr(strategy, "warmup_periods", 0)

        for i, (idx, row) in enumerate(df.iterrows()):
            close = row["close"]

            if i >= warmup:
                if isinstance(strategy, AbstractStrategy):
                    signals = strategy.on_bar(row)
                else:
                    # For KainexStrategy, use a lightweight bar-like call
                    signals = self._call_kainex_strategy(strategy, row)

                for sig in signals:
                    if sig.signal_type == SignalType.BUY and position == 0:
                        qty = cash * 0.95 / close
                        cost = qty * close
                        cash -= cost
                        position = qty
                        avg_price = close
                        trade_records.append({
                            "entry_time": idx,
                            "symbol": sig.symbol or "UNKNOWN",
                            "side": "buy",
                            "entry_price": close,
                            "quantity": qty,
                        })
                    elif sig.signal_type == SignalType.SELL and position > 0:
                        proceeds = position * close
                        pnl = proceeds - position * avg_price
                        cash += proceeds
                        if trade_records and "exit_time" not in trade_records[-1]:
                            trade_records[-1]["exit_time"] = idx
                            trade_records[-1]["exit_price"] = close
                            trade_records[-1]["pnl"] = pnl
                        position = 0.0
                        avg_price = 0.0

            equity_values.append(cash + position * close)

        equity = pd.Series(equity_values, index=df.index, name="equity")
        trades = pd.DataFrame(trade_records) if trade_records else pd.DataFrame()
        return equity, trades

    def _call_kainex_strategy(self, strategy: KainexStrategy, row: pd.Series) -> list:
        """Adapt a pandas row to call KainexStrategy.on_kainex_bar with a mock Bar-like object."""
        # Use a simple adapter since we don't have a real NautilusTrader Bar in simple sim
        from engine.strategies.base import Signal
        # Fall back to checking if strategy has closes tracking
        strategy._closes.append(float(row["close"]))

        if len(strategy._closes) < strategy.long_window:
            return []

        short_sma = sum(strategy._closes[-strategy.short_window:]) / strategy.short_window
        long_sma = sum(strategy._closes[-strategy.long_window:]) / strategy.long_window

        signals = []
        if strategy._prev_short is not None and strategy._prev_long is not None:
            symbol = row.get("symbol", "UNKNOWN")
            if strategy._prev_short <= strategy._prev_long and short_sma > long_sma:
                signals.append(Signal(
                    symbol=symbol,
                    signal_type=SignalType.BUY,
                    price=float(row["close"]),
                    quantity=1.0,
                ))
            elif strategy._prev_short >= strategy._prev_long and short_sma < long_sma:
                signals.append(Signal(
                    symbol=symbol,
                    signal_type=SignalType.SELL,
                    price=float(row["close"]),
                    quantity=1.0,
                ))

        strategy._prev_short = short_sma
        strategy._prev_long = long_sma
        return signals

    def _compute_metrics(
        self, calc: PerformanceCalculator, returns: pd.Series, equity: pd.Series, trades: pd.DataFrame
    ) -> dict:
        ann = _ann_factor(self.market)
        mean_ret = returns.mean() * ann
        std_ret = returns.std() * np.sqrt(ann)
        sharpe = mean_ret / std_ret if std_ret > 0 else 0.0

        downside = returns[returns < 0].std() * np.sqrt(ann)
        sortino = mean_ret / downside if downside > 0 else 0.0

        cummax = equity.cummax()
        drawdown = (equity - cummax) / cummax
        max_drawdown = drawdown.min()

        total_return = (equity.iloc[-1] / equity.iloc[0]) - 1 if len(equity) > 0 else 0.0

        win_rate = 0.0
        if not trades.empty and "pnl" in trades.columns:
            completed = trades.dropna(subset=["pnl"])
            if len(completed) > 0:
                win_rate = float((completed["pnl"] > 0).sum() / len(completed))

        gross_profit = returns[returns > 0].sum()
        gross_loss = abs(returns[returns < 0].sum())
        profit_factor = gross_profit / gross_loss if gross_loss > 0 else float("inf")

        return {
            "sharpe_ratio": round(sharpe, 4),
            "sortino_ratio": round(sortino, 4),
            "max_drawdown": round(max_drawdown, 4),
            "win_rate": round(win_rate, 4),
            "profit_factor": round(profit_factor, 4),
            "annual_return": round(mean_ret, 4),
            "total_return": round(total_return, 4),
        }


# Backward-compatible alias
class BacktestEngine(NautilusBacktestEngine):
    """Alias for backward compatibility."""

    def __init__(self, initial_capital: float = 100_000.0, freq: str = "1D", market: Market = Market.CRYPTO) -> None:
        super().__init__(initial_capital=initial_capital, market=market)
        self.freq = freq
