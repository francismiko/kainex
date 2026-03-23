import numpy as np
import pandas as pd

from engine.strategies.base import Market


def _ann_factor_for_market(market: Market) -> int:
    if market == Market.CRYPTO:
        return 365
    return 252  # A_STOCK, US_STOCK


class PerformanceCalculator:
    """Computes portfolio performance metrics."""

    def __init__(
        self,
        risk_free_rate: float = 0.02,
        ann_factor: int | None = None,
        market: Market | None = None,
    ) -> None:
        self.risk_free_rate = risk_free_rate
        if ann_factor is not None:
            self.ann_factor = ann_factor
        elif market is not None:
            self.ann_factor = _ann_factor_for_market(market)
        else:
            self.ann_factor = 252

    def sharpe_ratio(self, returns: pd.Series) -> float:
        excess = returns - self.risk_free_rate / self.ann_factor
        std = returns.std()
        if std == 0:
            return 0.0
        return float(excess.mean() / std * np.sqrt(self.ann_factor))

    def sortino_ratio(self, returns: pd.Series) -> float:
        excess = returns - self.risk_free_rate / self.ann_factor
        downside = returns[returns < 0].std()
        if downside == 0:
            return 0.0
        return float(excess.mean() / downside * np.sqrt(self.ann_factor))

    def calmar_ratio(self, returns: pd.Series) -> float:
        ann_return = self.annualized_return(returns)
        dd = abs(self.max_drawdown(returns))
        if dd == 0:
            return 0.0
        return ann_return / dd

    def max_drawdown(self, returns: pd.Series) -> float:
        cumulative = (1 + returns).cumprod()
        peak = cumulative.cummax()
        drawdown = (cumulative - peak) / peak
        return float(drawdown.min())

    def max_drawdown_duration(self, returns: pd.Series) -> int:
        """Max drawdown duration in bars."""
        cumulative = (1 + returns).cumprod()
        peak = cumulative.cummax()
        in_drawdown = cumulative < peak
        if not in_drawdown.any():
            return 0
        groups = (~in_drawdown).cumsum()
        dd_groups = groups[in_drawdown]
        if dd_groups.empty:
            return 0
        return int(dd_groups.value_counts().max())

    def win_rate_from_returns(self, returns: pd.Series) -> float:
        """Win rate based on daily returns (legacy)."""
        if len(returns) == 0:
            return 0.0
        return float((returns > 0).sum() / len(returns))

    def win_rate(
        self,
        trades: pd.DataFrame | pd.Series | None = None,
        returns: pd.Series | None = None,
    ) -> float:
        """Win rate based on trades (preferred) or daily returns (fallback).

        If *trades* is a DataFrame, expects a 'pnl' column.
        If *trades* is a Series, treats each value as a trade PnL.
        """
        if trades is not None:
            if isinstance(trades, pd.DataFrame):
                if trades.empty:
                    return 0.0
                pnl = (
                    trades["pnl"] if "pnl" in trades.columns else pd.Series(dtype=float)
                )
            else:
                pnl = trades
            if len(pnl) == 0:
                return 0.0
            return float((pnl > 0).sum() / len(pnl))
        if returns is not None:
            return self.win_rate_from_returns(returns)
        return 0.0

    def profit_loss_ratio(self, returns: pd.Series) -> float:
        wins = returns[returns > 0]
        losses = returns[returns < 0]
        if len(losses) == 0 or losses.mean() == 0:
            return float("inf")
        return float(abs(wins.mean() / losses.mean()))

    def profit_factor(self, returns: pd.Series) -> float:
        gross_profit = returns[returns > 0].sum()
        gross_loss = abs(returns[returns < 0].sum())
        if gross_loss == 0:
            return float("inf")
        return float(gross_profit / gross_loss)

    def annualized_return(self, returns: pd.Series) -> float:
        if len(returns) == 0:
            return 0.0
        total = (1 + returns).prod()
        n_years = len(returns) / self.ann_factor
        if n_years == 0:
            return 0.0
        return float(total ** (1 / n_years) - 1)

    def summary(self, returns: pd.Series, trades: pd.DataFrame | None = None) -> dict:
        return {
            "sharpe_ratio": round(self.sharpe_ratio(returns), 4),
            "sortino_ratio": round(self.sortino_ratio(returns), 4),
            "calmar_ratio": round(self.calmar_ratio(returns), 4),
            "max_drawdown": round(self.max_drawdown(returns), 4),
            "max_drawdown_duration": self.max_drawdown_duration(returns),
            "win_rate": round(self.win_rate(trades=trades, returns=returns), 4),
            "profit_loss_ratio": round(self.profit_loss_ratio(returns), 4),
            "profit_factor": round(self.profit_factor(returns), 4),
            "annualized_return": round(self.annualized_return(returns), 4),
        }
