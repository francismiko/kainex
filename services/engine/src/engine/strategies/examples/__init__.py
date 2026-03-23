"""Example strategies."""

from engine.strategies.examples.sma_crossover import (
    SmaCrossoverLegacy,
    SmaCrossoverStrategy,
)
from engine.strategies.examples.rsi_mean_reversion import RsiMeanReversion
from engine.strategies.examples.bollinger_breakout import BollingerBreakout
from engine.strategies.examples.macd_crossover import MacdCrossover
from engine.strategies.examples.momentum import MomentumStrategy
from engine.strategies.examples.dual_ma import DualMaStrategy
from engine.strategies.examples.ml_signal import MLSignalStrategy
from engine.strategies.examples.pairs_trading import PairsTradingStrategy
from engine.strategies.examples.grid_trading import GridTradingStrategy
from engine.strategies.examples.donchian_breakout import DonchianBreakoutStrategy
from engine.strategies.examples.funding_rate_arb import FundingRateArbStrategy

__all__ = [
    "SmaCrossoverLegacy",
    "SmaCrossoverStrategy",
    "RsiMeanReversion",
    "BollingerBreakout",
    "MacdCrossover",
    "MomentumStrategy",
    "DualMaStrategy",
    "MLSignalStrategy",
    "PairsTradingStrategy",
    "GridTradingStrategy",
    "DonchianBreakoutStrategy",
    "FundingRateArbStrategy",
]
