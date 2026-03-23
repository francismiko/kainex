"""Example strategies."""

from engine.strategies.examples.sma_crossover import SmaCrossoverLegacy, SmaCrossoverStrategy
from engine.strategies.examples.rsi_mean_reversion import RsiMeanReversion
from engine.strategies.examples.bollinger_breakout import BollingerBreakout
from engine.strategies.examples.macd_crossover import MacdCrossover
from engine.strategies.examples.momentum import MomentumStrategy
from engine.strategies.examples.dual_ma import DualMaStrategy

__all__ = [
    "SmaCrossoverLegacy",
    "SmaCrossoverStrategy",
    "RsiMeanReversion",
    "BollingerBreakout",
    "MacdCrossover",
    "MomentumStrategy",
    "DualMaStrategy",
]
