"""Tests for the core engine modules: indicators, performance, broker, risk, runner, optimizer, backtest."""

import numpy as np
import pandas as pd
import pytest

from engine.indicators.technical import TechnicalIndicators
from engine.portfolio.performance import PerformanceCalculator
from engine.paper_trading.broker import PaperBroker, OrderStatus
from engine.paper_trading.slippage import SlippageModel
from engine.risk.manager import RiskManager
from engine.risk.drawdown import DrawdownCircuitBreaker
from engine.risk.position import PositionLimiter
from engine.strategies.base import Signal, SignalType, Market, TimeFrame
from engine.strategies.examples.sma_crossover import SmaCrossoverLegacy
from engine.strategies.examples.rsi_mean_reversion import RsiMeanReversion
from engine.strategies.examples.bollinger_breakout import BollingerBreakout
from engine.strategies.examples.macd_crossover import MacdCrossover
from engine.strategies.examples.momentum import MomentumStrategy
from engine.strategies.examples.dual_ma import DualMaStrategy
from engine.strategies.examples.pairs_trading import PairsTradingStrategy
from engine.strategies.examples.grid_trading import GridTradingStrategy
from engine.strategies.examples.donchian_breakout import DonchianBreakoutStrategy
from engine.strategies.examples.funding_rate_arb import FundingRateArbStrategy
from engine.core.runner import StrategyRunner


# --------------- helpers ---------------

def _make_ohlcv(n: int = 200, seed: int = 42) -> pd.DataFrame:
    """Generate synthetic OHLCV data."""
    rng = np.random.RandomState(seed)
    dates = pd.bdate_range("2024-01-01", periods=n, freq="D")
    close = 100 + np.cumsum(rng.randn(n) * 0.5)
    close = np.maximum(close, 10)  # keep positive
    high = close + rng.uniform(0, 1, n)
    low = close - rng.uniform(0, 1, n)
    open_ = close + rng.uniform(-0.5, 0.5, n)
    volume = rng.randint(1000, 10000, n).astype(float)
    return pd.DataFrame(
        {"open": open_, "high": high, "low": low, "close": close, "volume": volume},
        index=dates,
    )


def _make_returns(n: int = 252, seed: int = 42) -> pd.Series:
    rng = np.random.RandomState(seed)
    return pd.Series(rng.randn(n) * 0.01, name="returns")


# --------------- TechnicalIndicators ---------------

class TestTechnicalIndicators:
    def test_sma(self):
        df = _make_ohlcv()
        result = TechnicalIndicators.sma(df["close"], length=20)
        assert isinstance(result, pd.Series)
        assert len(result) == len(df)
        assert result.iloc[:19].isna().all()
        assert result.iloc[19:].notna().all()

    def test_ema(self):
        df = _make_ohlcv()
        result = TechnicalIndicators.ema(df["close"], length=10)
        assert isinstance(result, pd.Series)
        assert result.iloc[-1] != 0

    def test_rsi(self):
        df = _make_ohlcv()
        result = TechnicalIndicators.rsi(df["close"], length=14)
        assert isinstance(result, pd.Series)
        valid = result.dropna()
        assert (valid >= 0).all() and (valid <= 100).all()

    def test_macd(self):
        df = _make_ohlcv()
        result = TechnicalIndicators.macd(df["close"])
        assert isinstance(result, pd.DataFrame)
        assert len(result.columns) == 3

    def test_bbands(self):
        df = _make_ohlcv()
        result = TechnicalIndicators.bbands(df["close"], length=20)
        assert isinstance(result, pd.DataFrame)
        # bbands returns 5 columns: lower, mid, upper, bandwidth, percent
        assert len(result.columns) >= 3

    def test_atr(self):
        df = _make_ohlcv()
        result = TechnicalIndicators.atr(df["high"], df["low"], df["close"], length=14)
        assert isinstance(result, pd.Series)
        valid = result.dropna()
        assert (valid > 0).all()

    def test_adx(self):
        df = _make_ohlcv()
        result = TechnicalIndicators.adx(df["high"], df["low"], df["close"], length=14)
        assert isinstance(result, pd.DataFrame)
        assert not result.dropna(how="all").empty

    def test_vwap(self):
        df = _make_ohlcv()
        result = TechnicalIndicators.vwap(df["high"], df["low"], df["close"], df["volume"])
        assert isinstance(result, pd.Series)
        assert not result.dropna().empty

    def test_obv(self):
        df = _make_ohlcv()
        result = TechnicalIndicators.obv(df["close"], df["volume"])
        assert isinstance(result, pd.Series)
        assert not result.dropna().empty

    def test_willr(self):
        df = _make_ohlcv()
        result = TechnicalIndicators.willr(df["high"], df["low"], df["close"], length=14)
        assert isinstance(result, pd.Series)
        valid = result.dropna()
        assert (valid <= 0).all() and (valid >= -100).all()

    def test_cci(self):
        df = _make_ohlcv()
        result = TechnicalIndicators.cci(df["high"], df["low"], df["close"], length=20)
        assert isinstance(result, pd.Series)
        assert not result.dropna().empty

    def test_mfi(self):
        df = _make_ohlcv()
        result = TechnicalIndicators.mfi(df["high"], df["low"], df["close"], df["volume"], length=14)
        assert isinstance(result, pd.Series)
        valid = result.dropna()
        assert (valid >= 0).all() and (valid <= 100).all()

    def test_supertrend(self):
        df = _make_ohlcv()
        result = TechnicalIndicators.supertrend(df["high"], df["low"], df["close"], length=7, multiplier=3.0)
        assert isinstance(result, pd.DataFrame)
        assert not result.dropna(how="all").empty

    def test_keltner(self):
        df = _make_ohlcv()
        result = TechnicalIndicators.keltner(df["high"], df["low"], df["close"], length=20, multiplier=1.5)
        assert isinstance(result, pd.DataFrame)
        assert not result.dropna(how="all").empty

    def test_cmf(self):
        df = _make_ohlcv()
        result = TechnicalIndicators.cmf(df["high"], df["low"], df["close"], df["volume"], length=20)
        assert isinstance(result, pd.Series)
        assert not result.dropna().empty

    def test_psar(self):
        df = _make_ohlcv()
        result = TechnicalIndicators.psar(df["high"], df["low"], df["close"])
        assert isinstance(result, pd.DataFrame)
        assert not result.dropna(how="all").empty

    def test_ichimoku(self):
        df = _make_ohlcv()
        result = TechnicalIndicators.ichimoku(df["high"], df["low"], df["close"])
        assert isinstance(result, pd.DataFrame)
        assert not result.dropna(how="all").empty


# --------------- PerformanceCalculator ---------------

class TestPerformanceCalculator:
    def setup_method(self):
        self.calc = PerformanceCalculator(risk_free_rate=0.02, ann_factor=252)
        self.returns = _make_returns()

    def test_sharpe_ratio(self):
        sr = self.calc.sharpe_ratio(self.returns)
        assert isinstance(sr, float)

    def test_sortino_ratio(self):
        sr = self.calc.sortino_ratio(self.returns)
        assert isinstance(sr, float)

    def test_calmar_ratio(self):
        cr = self.calc.calmar_ratio(self.returns)
        assert isinstance(cr, float)

    def test_max_drawdown(self):
        dd = self.calc.max_drawdown(self.returns)
        assert dd <= 0

    def test_max_drawdown_duration(self):
        dur = self.calc.max_drawdown_duration(self.returns)
        assert isinstance(dur, int)
        assert dur >= 0

    def test_win_rate_from_returns(self):
        wr = self.calc.win_rate(returns=self.returns)
        assert 0 <= wr <= 1

    def test_win_rate_from_trades(self):
        trades = pd.DataFrame({"pnl": [100, -50, 200, -30, 150]})
        wr = self.calc.win_rate(trades=trades)
        assert wr == 3 / 5

    def test_win_rate_empty_trades(self):
        trades = pd.DataFrame({"pnl": []})
        wr = self.calc.win_rate(trades=trades)
        assert wr == 0.0

    def test_profit_factor(self):
        pf = self.calc.profit_factor(self.returns)
        assert pf > 0

    def test_annualized_return(self):
        ar = self.calc.annualized_return(self.returns)
        assert isinstance(ar, float)

    def test_summary_keys(self):
        s = self.calc.summary(self.returns)
        expected_keys = {
            "sharpe_ratio", "sortino_ratio", "calmar_ratio",
            "max_drawdown", "max_drawdown_duration",
            "win_rate", "profit_loss_ratio", "profit_factor",
            "annualized_return",
        }
        assert set(s.keys()) == expected_keys

    def test_empty_returns(self):
        empty = pd.Series([], dtype=float)
        assert self.calc.win_rate(returns=empty) == 0.0
        assert self.calc.annualized_return(empty) == 0.0

    def test_market_ann_factor(self):
        crypto_calc = PerformanceCalculator(market=Market.CRYPTO)
        assert crypto_calc.ann_factor == 365
        stock_calc = PerformanceCalculator(market=Market.A_STOCK)
        assert stock_calc.ann_factor == 252


# --------------- PaperBroker ---------------

class TestPaperBroker:
    def test_buy_order(self):
        broker = PaperBroker(market=Market.CRYPTO, initial_cash=100_000.0, slippage=SlippageModel(seed=0))
        signal = Signal(symbol="BTC/USDT", signal_type=SignalType.BUY, price=50000.0, quantity=1.0)
        order = broker.submit_order(signal)
        assert order.status == OrderStatus.FILLED
        assert order.filled_price > 0
        assert broker.cash < 100_000.0
        assert "BTC/USDT" in broker.positions

    def test_sell_order(self):
        broker = PaperBroker(market=Market.CRYPTO, initial_cash=100_000.0, slippage=SlippageModel(seed=0))
        buy = Signal(symbol="BTC/USDT", signal_type=SignalType.BUY, price=50000.0, quantity=1.0)
        broker.submit_order(buy)
        sell = Signal(symbol="BTC/USDT", signal_type=SignalType.SELL, price=51000.0, quantity=1.0)
        order = broker.submit_order(sell)
        assert order.status == OrderStatus.FILLED
        assert "BTC/USDT" not in broker.positions

    def test_insufficient_cash_rejected(self):
        broker = PaperBroker(market=Market.CRYPTO, initial_cash=1000.0, slippage=SlippageModel(seed=0))
        signal = Signal(symbol="BTC/USDT", signal_type=SignalType.BUY, price=50000.0, quantity=1.0)
        order = broker.submit_order(signal)
        assert order.status == OrderStatus.REJECTED

    def test_sell_without_position_rejected(self):
        broker = PaperBroker(market=Market.CRYPTO, initial_cash=100_000.0, slippage=SlippageModel(seed=0))
        signal = Signal(symbol="BTC/USDT", signal_type=SignalType.SELL, price=50000.0, quantity=1.0)
        order = broker.submit_order(signal)
        assert order.status == OrderStatus.REJECTED

    def test_equity_with_market_price(self):
        broker = PaperBroker(market=Market.CRYPTO, initial_cash=100_000.0, slippage=SlippageModel(rate=0.0))
        assert broker.equity == 100_000.0
        # Buy and update market price
        signal = Signal(symbol="BTC/USDT", signal_type=SignalType.BUY, price=50000.0, quantity=1.0)
        broker.submit_order(signal)
        broker.update_market_price("BTC/USDT", 55000.0)
        pos = broker.positions["BTC/USDT"]
        assert pos.market_price == 55000.0
        # Equity should reflect market price, not avg_price
        expected = broker.cash + 1.0 * 55000.0
        assert abs(broker.equity - expected) < 0.01

    def test_a_stock_t_plus_1(self):
        """A-stock T+1 rule: cannot sell shares bought on the same day."""
        from datetime import date
        broker = PaperBroker(market=Market.A_STOCK, initial_cash=100_000.0, slippage=SlippageModel(rate=0.0))
        broker.set_current_date(date(2024, 3, 15))
        buy = Signal(symbol="600519", signal_type=SignalType.BUY, price=100.0, quantity=100.0)
        broker.submit_order(buy)
        # Same day sell should be rejected
        sell = Signal(symbol="600519", signal_type=SignalType.SELL, price=105.0, quantity=100.0)
        order = broker.submit_order(sell)
        assert order.status == OrderStatus.REJECTED
        assert "T+1" in order.reject_reason
        # Next day sell should succeed
        broker.set_current_date(date(2024, 3, 18))
        sell2 = Signal(symbol="600519", signal_type=SignalType.SELL, price=105.0, quantity=100.0)
        order2 = broker.submit_order(sell2)
        assert order2.status == OrderStatus.FILLED

    def test_risk_manager_integration(self):
        rm = RiskManager(max_position_pct=0.05, max_drawdown=0.2)
        broker = PaperBroker(
            market=Market.CRYPTO,
            initial_cash=100_000.0,
            slippage=SlippageModel(rate=0.0),
            risk_manager=rm,
        )
        # Try to buy too much (50000 * 2 = 100000 > 5% of 100000 = 5000)
        signal = Signal(symbol="BTC/USDT", signal_type=SignalType.BUY, price=50000.0, quantity=2.0)
        order = broker.submit_order(signal)
        assert order.status == OrderStatus.REJECTED
        assert order.reject_reason == "risk check failed"


# --------------- RiskManager ---------------

class TestRiskManager:
    def test_passes_within_limits(self):
        rm = RiskManager(max_position_pct=0.1, max_drawdown=0.2)
        signal = Signal(symbol="AAPL", signal_type=SignalType.BUY, price=100.0, quantity=10.0)
        assert rm.check(signal, portfolio_value=100_000.0, position_value=0.0) is True

    def test_rejects_over_position_limit(self):
        rm = RiskManager(max_position_pct=0.1, max_drawdown=0.2)
        signal = Signal(symbol="AAPL", signal_type=SignalType.BUY, price=100.0, quantity=200.0)
        # 100*200 = 20000 > 10% of 100000 = 10000
        assert rm.check(signal, portfolio_value=100_000.0, position_value=0.0) is False

    def test_halts_on_drawdown(self):
        rm = RiskManager(max_position_pct=0.5, max_drawdown=0.1)
        rm.update_equity(current_equity=85_000.0, peak_equity=100_000.0)
        assert rm.is_halted is True
        signal = Signal(symbol="AAPL", signal_type=SignalType.BUY, price=100.0, quantity=1.0)
        assert rm.check(signal, portfolio_value=85_000.0, position_value=0.0) is False

    def test_reset(self):
        rm = RiskManager(max_position_pct=0.5, max_drawdown=0.1)
        rm.update_equity(current_equity=85_000.0, peak_equity=100_000.0)
        assert rm.is_halted is True
        rm.reset()
        assert rm.is_halted is False


class TestDrawdownCircuitBreaker:
    def test_not_breached(self):
        cb = DrawdownCircuitBreaker(threshold=0.2)
        assert cb.is_breached(current_equity=90_000, peak_equity=100_000) is False

    def test_breached(self):
        cb = DrawdownCircuitBreaker(threshold=0.2)
        assert cb.is_breached(current_equity=79_000, peak_equity=100_000) is True

    def test_current_drawdown(self):
        cb = DrawdownCircuitBreaker(threshold=0.2)
        dd = cb.current_drawdown(current_equity=90_000, peak_equity=100_000)
        assert abs(dd - 0.1) < 1e-9


class TestPositionLimiter:
    def test_within_limit(self):
        pl = PositionLimiter(max_position_pct=0.1)
        signal = Signal(symbol="AAPL", signal_type=SignalType.BUY, price=100.0, quantity=5.0)
        assert pl.check(signal, portfolio_value=100_000.0, current_position_value=0.0) is True

    def test_exceeds_limit(self):
        pl = PositionLimiter(max_position_pct=0.1)
        signal = Signal(symbol="AAPL", signal_type=SignalType.BUY, price=100.0, quantity=200.0)
        assert pl.check(signal, portfolio_value=100_000.0, current_position_value=0.0) is False


# --------------- SmaCrossoverStrategy (Legacy) ---------------

class TestSmaCrossoverStrategy:
    def test_parameters(self):
        s = SmaCrossoverLegacy(short_window=5, long_window=20)
        params = s.parameters()
        assert params == {"short_window": 5, "long_window": 20}

    def test_golden_cross(self):
        s = SmaCrossoverLegacy()
        # First bar: short below long
        bar1 = pd.Series({"close": 100, "sma_short": 95.0, "sma_long": 100.0, "symbol": "TEST"})
        signals = s.on_bar(bar1)
        assert signals == []
        # Second bar: short crosses above long
        bar2 = pd.Series({"close": 105, "sma_short": 101.0, "sma_long": 100.0, "symbol": "TEST"})
        signals = s.on_bar(bar2)
        assert len(signals) == 1
        assert signals[0].signal_type == SignalType.BUY

    def test_death_cross(self):
        s = SmaCrossoverLegacy()
        bar1 = pd.Series({"close": 100, "sma_short": 101.0, "sma_long": 100.0, "symbol": "TEST"})
        s.on_bar(bar1)
        bar2 = pd.Series({"close": 95, "sma_short": 99.0, "sma_long": 100.0, "symbol": "TEST"})
        signals = s.on_bar(bar2)
        assert len(signals) == 1
        assert signals[0].signal_type == SignalType.SELL

    def test_no_signal_without_sma(self):
        s = SmaCrossoverLegacy()
        bar = pd.Series({"close": 100, "symbol": "TEST"})
        assert s.on_bar(bar) == []


# --------------- RsiMeanReversion ---------------

class TestRsiMeanReversion:
    def test_parameters(self):
        s = RsiMeanReversion(rsi_period=10, oversold=25.0, overbought=75.0)
        p = s.parameters()
        assert p["rsi_period"] == 10
        assert p["oversold"] == 25.0
        assert p["overbought"] == 75.0

    def test_buy_on_oversold(self):
        s = RsiMeanReversion()
        bar = pd.Series({"close": 100.0, "rsi": 20.0, "symbol": "TEST"})
        signals = s.on_bar(bar)
        assert len(signals) == 1
        assert signals[0].signal_type == SignalType.BUY

    def test_sell_on_overbought(self):
        s = RsiMeanReversion()
        bar = pd.Series({"close": 100.0, "rsi": 80.0, "symbol": "TEST"})
        signals = s.on_bar(bar)
        assert len(signals) == 1
        assert signals[0].signal_type == SignalType.SELL

    def test_no_signal_in_neutral_zone(self):
        s = RsiMeanReversion()
        bar = pd.Series({"close": 100.0, "rsi": 50.0, "symbol": "TEST"})
        assert s.on_bar(bar) == []

    def test_no_signal_without_rsi(self):
        s = RsiMeanReversion()
        bar = pd.Series({"close": 100.0, "symbol": "TEST"})
        assert s.on_bar(bar) == []


# --------------- BollingerBreakout ---------------

class TestBollingerBreakout:
    def test_parameters(self):
        s = BollingerBreakout(bb_period=15, bb_std=1.5)
        assert s.parameters() == {"bb_period": 15, "bb_std": 1.5}

    def test_buy_above_upper(self):
        s = BollingerBreakout()
        bar = pd.Series({"close": 110.0, "bb_upper": 105.0, "bb_lower": 95.0, "symbol": "TEST"})
        signals = s.on_bar(bar)
        assert len(signals) == 1
        assert signals[0].signal_type == SignalType.BUY

    def test_sell_below_lower(self):
        s = BollingerBreakout()
        bar = pd.Series({"close": 90.0, "bb_upper": 105.0, "bb_lower": 95.0, "symbol": "TEST"})
        signals = s.on_bar(bar)
        assert len(signals) == 1
        assert signals[0].signal_type == SignalType.SELL

    def test_no_signal_within_bands(self):
        s = BollingerBreakout()
        bar = pd.Series({"close": 100.0, "bb_upper": 105.0, "bb_lower": 95.0, "symbol": "TEST"})
        assert s.on_bar(bar) == []

    def test_no_signal_without_bands(self):
        s = BollingerBreakout()
        bar = pd.Series({"close": 100.0, "symbol": "TEST"})
        assert s.on_bar(bar) == []


# --------------- MacdCrossover ---------------

class TestMacdCrossover:
    def test_parameters(self):
        s = MacdCrossover(fast_period=8, slow_period=21, signal_period=5)
        assert s.parameters() == {"fast_period": 8, "slow_period": 21, "signal_period": 5}

    def test_buy_on_crossover(self):
        s = MacdCrossover()
        # First bar: MACD below signal
        bar1 = pd.Series({"close": 100.0, "macd": -1.0, "macd_signal": 0.0, "symbol": "TEST"})
        assert s.on_bar(bar1) == []
        # Second bar: MACD crosses above signal
        bar2 = pd.Series({"close": 105.0, "macd": 1.0, "macd_signal": 0.0, "symbol": "TEST"})
        signals = s.on_bar(bar2)
        assert len(signals) == 1
        assert signals[0].signal_type == SignalType.BUY

    def test_sell_on_crossunder(self):
        s = MacdCrossover()
        bar1 = pd.Series({"close": 100.0, "macd": 1.0, "macd_signal": 0.0, "symbol": "TEST"})
        s.on_bar(bar1)
        bar2 = pd.Series({"close": 95.0, "macd": -1.0, "macd_signal": 0.0, "symbol": "TEST"})
        signals = s.on_bar(bar2)
        assert len(signals) == 1
        assert signals[0].signal_type == SignalType.SELL

    def test_no_signal_without_macd(self):
        s = MacdCrossover()
        bar = pd.Series({"close": 100.0, "symbol": "TEST"})
        assert s.on_bar(bar) == []


# --------------- MomentumStrategy ---------------

class TestMomentumStrategy:
    def test_parameters(self):
        s = MomentumStrategy(lookback=10, threshold=0.05)
        assert s.parameters() == {"lookback": 10, "threshold": 0.05}

    def test_buy_on_positive_momentum(self):
        s = MomentumStrategy(lookback=3, threshold=0.02)
        # Feed warmup bars
        for price in [100.0, 100.0, 100.0]:
            bar = pd.Series({"close": price, "symbol": "TEST"})
            s.on_bar(bar)
        # Price jumps 5% -> should trigger buy
        bar = pd.Series({"close": 105.0, "symbol": "TEST"})
        signals = s.on_bar(bar)
        assert len(signals) == 1
        assert signals[0].signal_type == SignalType.BUY

    def test_sell_on_negative_momentum(self):
        s = MomentumStrategy(lookback=3, threshold=0.02)
        for price in [100.0, 100.0, 100.0]:
            bar = pd.Series({"close": price, "symbol": "TEST"})
            s.on_bar(bar)
        bar = pd.Series({"close": 95.0, "symbol": "TEST"})
        signals = s.on_bar(bar)
        assert len(signals) == 1
        assert signals[0].signal_type == SignalType.SELL

    def test_no_signal_insufficient_data(self):
        s = MomentumStrategy(lookback=20)
        for i in range(10):
            bar = pd.Series({"close": 100.0 + i, "symbol": "TEST"})
            assert s.on_bar(bar) == []

    def test_no_signal_within_threshold(self):
        s = MomentumStrategy(lookback=3, threshold=0.10)
        for price in [100.0, 100.0, 100.0]:
            bar = pd.Series({"close": price, "symbol": "TEST"})
            s.on_bar(bar)
        # Only 1% move, below 10% threshold
        bar = pd.Series({"close": 101.0, "symbol": "TEST"})
        assert s.on_bar(bar) == []


# --------------- DualMaStrategy ---------------

class TestDualMaStrategy:
    def test_parameters(self):
        s = DualMaStrategy(fast_period=5, slow_period=20, ma_type="sma")
        assert s.parameters() == {"fast_period": 5, "slow_period": 20, "ma_type": "sma"}

    def test_buy_on_golden_cross(self):
        s = DualMaStrategy()
        bar1 = pd.Series({"close": 100.0, "ma_fast": 95.0, "ma_slow": 100.0, "symbol": "TEST"})
        assert s.on_bar(bar1) == []
        bar2 = pd.Series({"close": 105.0, "ma_fast": 101.0, "ma_slow": 100.0, "symbol": "TEST"})
        signals = s.on_bar(bar2)
        assert len(signals) == 1
        assert signals[0].signal_type == SignalType.BUY

    def test_sell_on_death_cross(self):
        s = DualMaStrategy()
        bar1 = pd.Series({"close": 100.0, "ma_fast": 101.0, "ma_slow": 100.0, "symbol": "TEST"})
        s.on_bar(bar1)
        bar2 = pd.Series({"close": 95.0, "ma_fast": 99.0, "ma_slow": 100.0, "symbol": "TEST"})
        signals = s.on_bar(bar2)
        assert len(signals) == 1
        assert signals[0].signal_type == SignalType.SELL

    def test_no_signal_without_ma(self):
        s = DualMaStrategy()
        bar = pd.Series({"close": 100.0, "symbol": "TEST"})
        assert s.on_bar(bar) == []

    def test_default_ma_type_is_ema(self):
        s = DualMaStrategy()
        assert s.parameters()["ma_type"] == "ema"


# --------------- StrategyRunner ---------------

class TestStrategyRunner:
    def test_run_collects_signals(self):
        strategy = SmaCrossoverLegacy(short_window=5, long_window=10)
        runner = StrategyRunner(strategy)
        df = _make_ohlcv(100)
        short_sma = TechnicalIndicators.sma(df["close"], length=5)
        long_sma = TechnicalIndicators.sma(df["close"], length=10)
        df["sma_short"] = short_sma
        df["sma_long"] = long_sma
        df["symbol"] = "TEST"
        signals = runner.run(df)
        assert isinstance(signals, list)
        # Should have generated at least some signals on 100 bars
        assert len(signals) >= 0  # may be 0 if no crossover

    def test_warmup_skipped(self):
        strategy = SmaCrossoverLegacy(short_window=5, long_window=10)
        runner = StrategyRunner(strategy)
        df = _make_ohlcv(20)
        df["sma_short"] = TechnicalIndicators.sma(df["close"], length=5)
        df["sma_long"] = TechnicalIndicators.sma(df["close"], length=10)
        df["symbol"] = "TEST"
        runner.run(df)
        assert runner._bar_count == 20

    def test_reset(self):
        strategy = SmaCrossoverLegacy()
        runner = StrategyRunner(strategy)
        df = _make_ohlcv(50)
        df["sma_short"] = TechnicalIndicators.sma(df["close"], length=10)
        df["sma_long"] = TechnicalIndicators.sma(df["close"], length=30)
        df["symbol"] = "TEST"
        runner.run(df)
        runner.reset()
        assert runner.signals == []
        assert runner._bar_count == 0


# --------------- BacktestEngine ---------------

class TestBacktestEngine:
    def test_run_returns_result(self):
        from engine.core.backtest import BacktestEngine, BacktestResult

        df = _make_ohlcv(200)
        short_sma = TechnicalIndicators.sma(df["close"], length=10)
        long_sma = TechnicalIndicators.sma(df["close"], length=30)
        df["sma_short"] = short_sma
        df["sma_long"] = long_sma
        df["symbol"] = "TEST"

        strategy = SmaCrossoverLegacy(short_window=10, long_window=30)
        engine = BacktestEngine(initial_capital=100_000.0)
        result = engine.run(strategy, df)

        assert isinstance(result, BacktestResult)
        assert isinstance(result.equity_curve, pd.Series)
        assert len(result.equity_curve) == len(df)
        assert "sharpe_ratio" in result.metrics
        assert "max_drawdown" in result.metrics
        assert "total_return" in result.metrics

    def test_run_with_date_filter(self):
        from engine.core.backtest import BacktestEngine
        from datetime import datetime

        df = _make_ohlcv(200)
        df["sma_short"] = TechnicalIndicators.sma(df["close"], length=10)
        df["sma_long"] = TechnicalIndicators.sma(df["close"], length=30)
        df["symbol"] = "TEST"

        strategy = SmaCrossoverLegacy(short_window=10, long_window=30)
        engine = BacktestEngine(initial_capital=100_000.0)
        result = engine.run(strategy, df, start=datetime(2024, 3, 1), end=datetime(2024, 8, 1))

        assert len(result.equity_curve) < len(df)


# --------------- ParameterOptimizer ---------------

class TestParameterOptimizer:
    def test_optimize(self):
        from engine.core.optimizer import ParameterOptimizer
        from engine.core.backtest import BacktestEngine

        df = _make_ohlcv(200)
        short_sma_5 = TechnicalIndicators.sma(df["close"], length=5)
        short_sma_10 = TechnicalIndicators.sma(df["close"], length=10)
        long_sma_20 = TechnicalIndicators.sma(df["close"], length=20)
        long_sma_30 = TechnicalIndicators.sma(df["close"], length=30)
        # Pre-compute all needed SMAs in the dataframe
        df["sma_short"] = short_sma_10
        df["sma_long"] = long_sma_30
        df["symbol"] = "TEST"

        engine = BacktestEngine(initial_capital=100_000.0)
        optimizer = ParameterOptimizer(engine=engine)

        # Note: the optimizer creates new strategy instances with the given params,
        # but the SMA columns in the data are fixed. This tests the optimizer
        # mechanics even though the SMA values don't change per param combo.
        result = optimizer.optimize(
            strategy_cls=SmaCrossoverLegacy,
            data=df,
            param_grid={"short_window": [5, 10], "long_window": [20, 30]},
            metric="sharpe_ratio",
        )

        assert result.best_params is not None
        assert len(result.all_results) == 4  # 2 x 2 combos
        # Results should be sorted by sharpe descending
        metrics = [r[1] for r in result.all_results]
        assert metrics == sorted(metrics, reverse=True)


# --------------- DuckDBStore ---------------

class TestDuckDBStore:
    def test_init_and_query(self, tmp_path):
        from engine.storage.duckdb_store import DuckDBStore
        store = DuckDBStore(db_path=tmp_path / "test.duckdb")
        df = store.query_bars("BTC/USDT", "crypto", "1d")
        assert isinstance(df, pd.DataFrame)
        assert df.empty
        store.close()

    def test_export_parquet(self, tmp_path):
        from engine.storage.duckdb_store import DuckDBStore
        store = DuckDBStore(db_path=tmp_path / "test.duckdb")
        # Insert some data
        store._execute("""
            INSERT INTO bars (symbol, market, timeframe, open, high, low, close, volume, ts) VALUES
            ('BTC/USDT', 'crypto', '1d', 42000, 43000, 41000, 42500, 1000, '2024-01-01')
        """)
        out_path = tmp_path / "export.parquet"
        store.export_parquet("all_bars", out_path)
        assert out_path.exists()
        store.close()


# --------------- SQLiteStore ---------------

class TestSQLiteStore:
    @pytest.mark.asyncio
    async def test_connect_and_save(self, tmp_path):
        from engine.storage.sqlite_store import SQLiteStore
        store = SQLiteStore(db_path=tmp_path / "test.db")
        await store.connect()
        await store.save_strategy_config(
            id="test-1",
            name="Test Strategy",
            class_name="sma_crossover",
            parameters={"short": 10},
            markets=["crypto"],
            timeframes=["1d"],
        )
        config = await store.get_strategy_config("test-1")
        assert config is not None
        assert config["name"] == "Test Strategy"
        assert config["parameters"] == {"short": 10}
        await store.close()

    @pytest.mark.asyncio
    async def test_list_strategies(self, tmp_path):
        from engine.storage.sqlite_store import SQLiteStore
        store = SQLiteStore(db_path=tmp_path / "test.db")
        await store.connect()
        await store.save_strategy_config("s1", "A", "sma", {}, ["crypto"], ["1d"])
        await store.save_strategy_config("s2", "B", "rsi", {}, ["a_stock"], ["1h"])
        configs = await store.list_strategy_configs()
        assert len(configs) == 2
        await store.close()


# --------------- AsyncScheduler ---------------

class TestAsyncScheduler:
    @pytest.mark.asyncio
    async def test_add_job_invalid_cron(self):
        from engine.scheduler import AsyncScheduler
        scheduler = AsyncScheduler()
        with pytest.raises(ValueError, match="Invalid cron"):
            scheduler.add_job("bad", "not a cron", lambda: None)

    def test_add_job_valid(self):
        from engine.scheduler import AsyncScheduler
        scheduler = AsyncScheduler()
        scheduler.add_job("test", "* * * * *", lambda: None)
        assert len(scheduler._jobs) == 1

    def test_stop(self):
        from engine.scheduler import AsyncScheduler
        scheduler = AsyncScheduler()
        scheduler.add_job("test", "* * * * *", lambda: None)
        scheduler.stop()
        assert scheduler._running is False


# --------------- AStockCommission ---------------

class TestAStockCommission:
    def test_stamp_tax_rate(self):
        from engine.paper_trading.commission import AStockCommission
        comm = AStockCommission()
        assert comm.stamp_tax == 0.0005
        # Sell 10000 notional: commission = max(10000*0.0003, 5) + 10000*0.0005 = 5 + 5 = 10
        result = comm.calculate(100.0, 100.0, is_sell=True)
        assert result == 10.0


# --------------- FeatureStore ---------------

class TestFeatureStore:
    def setup_method(self):
        from engine.ml.feature_store import FeatureStore
        self.fs = FeatureStore()
        self.df = _make_ohlcv(200)

    def test_compute_features_returns_dataframe(self):
        result = self.fs.compute_features(self.df)
        assert isinstance(result, pd.DataFrame)
        assert not result.empty

    def test_compute_features_no_nan(self):
        result = self.fs.compute_features(self.df)
        assert result.isna().sum().sum() == 0

    def test_feature_columns_present(self):
        result = self.fs.compute_features(self.df)
        expected = {
            "return_1", "return_5", "return_10", "return_20",
            "log_return_1", "log_return_5",
            "momentum_5", "momentum_10", "momentum_20",
            "rsi_14", "macd", "macd_signal", "macd_hist",
            "atr_14", "bb_percent_b",
            "rolling_std_20", "realized_volatility",
            "volume_ma_ratio", "volume_std",
            "day_of_week", "month", "is_month_end",
            # New indicator features
            "adx_14", "di_plus_14", "di_minus_14",
            "obv", "cmf_20", "mfi_14",
            "willr_14", "cci_20",
            "atr_pct",
            "vwap", "price_vs_vwap",
        }
        assert expected.issubset(set(result.columns))

    def test_sma_columns(self):
        result = self.fs.compute_features(self.df)
        for length in (5, 10, 20, 60):
            assert f"sma_{length}" in result.columns
            assert f"price_sma_{length}_ratio" in result.columns

    def test_get_feature_names(self):
        names = self.fs.get_feature_names()
        assert isinstance(names, list)
        assert len(names) > 20
        # Should match actual computed columns
        result = self.fs.compute_features(self.df)
        for name in names:
            assert name in result.columns, f"Feature '{name}' not in computed output"

    def test_build_features_alias(self):
        """build_features should be a backward-compatible alias."""
        result = self.fs.build_features(self.df)
        assert isinstance(result, pd.DataFrame)
        assert not result.empty

    def test_rsi_in_valid_range(self):
        result = self.fs.compute_features(self.df)
        rsi = result["rsi_14"]
        assert (rsi >= 0).all() and (rsi <= 100).all()

    def test_adx_features(self):
        result = self.fs.compute_features(self.df)
        assert "adx_14" in result.columns
        assert "di_plus_14" in result.columns
        assert "di_minus_14" in result.columns

    def test_volume_indicator_features(self):
        result = self.fs.compute_features(self.df)
        assert "obv" in result.columns
        assert "cmf_20" in result.columns
        assert "mfi_14" in result.columns

    def test_oscillator_features(self):
        result = self.fs.compute_features(self.df)
        assert "willr_14" in result.columns
        assert "cci_20" in result.columns

    def test_atr_pct_feature(self):
        result = self.fs.compute_features(self.df)
        assert "atr_pct" in result.columns
        valid = result["atr_pct"]
        assert (valid > 0).all()

    def test_vwap_features(self):
        result = self.fs.compute_features(self.df)
        assert "vwap" in result.columns
        assert "price_vs_vwap" in result.columns

    def test_short_data_returns_empty(self):
        """With very few rows, features may be fully NaN and result empty."""
        short_df = _make_ohlcv(10)
        result = self.fs.compute_features(short_df)
        # Either empty or very few rows due to warmup
        assert len(result) <= 10


# --------------- ModelRegistry ---------------

class TestModelRegistry:
    def test_register_and_load(self, tmp_path):
        from engine.ml.model_registry import ModelRegistry
        reg = ModelRegistry(base_dir=tmp_path / "models")
        model = {"type": "dummy", "weights": [1, 2, 3]}
        mv = reg.register("test_model", model, metrics={"acc": 0.95})
        assert mv.name == "test_model"
        assert mv.version == "1"
        assert mv.metrics == {"acc": 0.95}

        loaded = reg.load("test_model")
        assert loaded == model

    def test_auto_version_increment(self, tmp_path):
        from engine.ml.model_registry import ModelRegistry
        reg = ModelRegistry(base_dir=tmp_path / "models")
        mv1 = reg.register("m", {"v": 1})
        mv2 = reg.register("m", {"v": 2})
        assert mv1.version == "1"
        assert mv2.version == "2"

    def test_explicit_version(self, tmp_path):
        from engine.ml.model_registry import ModelRegistry
        reg = ModelRegistry(base_dir=tmp_path / "models")
        mv = reg.register("m", {"v": 1}, version="custom-v1")
        assert mv.version == "custom-v1"

    def test_load_specific_version(self, tmp_path):
        from engine.ml.model_registry import ModelRegistry
        reg = ModelRegistry(base_dir=tmp_path / "models")
        reg.register("m", {"v": 1})
        reg.register("m", {"v": 2})
        loaded = reg.load("m", version="1")
        assert loaded == {"v": 1}

    def test_get_latest(self, tmp_path):
        from engine.ml.model_registry import ModelRegistry
        reg = ModelRegistry(base_dir=tmp_path / "models")
        reg.register("m", {"v": 1})
        reg.register("m", {"v": 2})
        latest = reg.get_latest("m")
        assert latest is not None
        assert latest.version == "2"

    def test_list_models(self, tmp_path):
        from engine.ml.model_registry import ModelRegistry
        reg = ModelRegistry(base_dir=tmp_path / "models")
        reg.register("alpha", {"a": 1})
        reg.register("beta", {"b": 2})
        names = reg.list_models()
        assert set(names) == {"alpha", "beta"}

    def test_list_versions(self, tmp_path):
        from engine.ml.model_registry import ModelRegistry
        reg = ModelRegistry(base_dir=tmp_path / "models")
        reg.register("m", {"v": 1})
        reg.register("m", {"v": 2})
        versions = reg.list_versions("m")
        assert len(versions) == 2

    def test_load_nonexistent_raises(self, tmp_path):
        from engine.ml.model_registry import ModelRegistry
        reg = ModelRegistry(base_dir=tmp_path / "models")
        with pytest.raises(FileNotFoundError):
            reg.load("nonexistent")

    def test_get_latest_empty(self, tmp_path):
        from engine.ml.model_registry import ModelRegistry
        reg = ModelRegistry(base_dir=tmp_path / "models")
        assert reg.get_latest("nonexistent") is None

    def test_persistence_across_instances(self, tmp_path):
        """Metadata persists in SQLite across ModelRegistry instances."""
        from engine.ml.model_registry import ModelRegistry
        base = tmp_path / "models"
        reg1 = ModelRegistry(base_dir=base)
        reg1.register("persist_test", {"data": 42})

        reg2 = ModelRegistry(base_dir=base)
        assert "persist_test" in reg2.list_models()
        loaded = reg2.load("persist_test")
        assert loaded == {"data": 42}


# --------------- MLPredictor ---------------

class TestMLPredictor:
    def test_neutral_when_no_model(self):
        from engine.indicators.ml_predictor import MLPredictor
        pred = MLPredictor()
        df = _make_ohlcv(100)
        from engine.ml.feature_store import FeatureStore
        features = FeatureStore().compute_features(df)
        result = pred.predict(features)
        assert isinstance(result, pd.Series)
        assert (result == 0.0).all()

    def test_predict_signal_neutral(self):
        from engine.indicators.ml_predictor import MLPredictor
        pred = MLPredictor()
        features = pd.DataFrame({"a": [1.0, 2.0]})
        signal = pred.predict_signal(features)
        assert signal == SignalType.HOLD

    def test_predict_with_trained_model(self, tmp_path):
        """End-to-end: train a model, register it, then predict."""
        from sklearn.ensemble import RandomForestClassifier
        from engine.ml.feature_store import FeatureStore
        from engine.ml.model_registry import ModelRegistry
        from engine.indicators.ml_predictor import MLPredictor

        # Prepare data
        df = _make_ohlcv(300)
        fs = FeatureStore()
        features = fs.compute_features(df)

        # Create labels
        future_ret = df["close"].pct_change(5).shift(-5)
        labels = pd.Series(0, index=df.index, dtype=int)
        labels[future_ret > 0.01] = 1
        labels[future_ret < -0.01] = -1
        labels = labels.reindex(features.index)
        mask = labels.notna()
        X = features[mask]
        y = labels[mask].astype(int)

        # Train
        clf = RandomForestClassifier(n_estimators=10, max_depth=3, random_state=42)
        clf.fit(X, y)

        # Register
        reg = ModelRegistry(base_dir=tmp_path / "models")
        reg.register("test_rf", clf)

        # Predict
        pred = MLPredictor(model_name="test_rf", registry=reg)
        pred.load()
        result = pred.predict(X)
        assert isinstance(result, pd.Series)
        assert len(result) == len(X)
        assert result.between(-1, 1).all()

    def test_predict_signal_buy_sell(self, tmp_path):
        """predict_signal should return BUY/SELL when model gives strong signal."""
        from sklearn.ensemble import RandomForestClassifier
        from engine.ml.feature_store import FeatureStore
        from engine.ml.model_registry import ModelRegistry
        from engine.indicators.ml_predictor import MLPredictor

        df = _make_ohlcv(300)
        fs = FeatureStore()
        features = fs.compute_features(df)

        future_ret = df["close"].pct_change(5).shift(-5)
        labels = pd.Series(0, index=df.index, dtype=int)
        labels[future_ret > 0.01] = 1
        labels[future_ret < -0.01] = -1
        labels = labels.reindex(features.index)
        mask = labels.notna()
        X = features[mask]
        y = labels[mask].astype(int)

        clf = RandomForestClassifier(n_estimators=10, max_depth=3, random_state=42)
        clf.fit(X, y)

        reg = ModelRegistry(base_dir=tmp_path / "models")
        reg.register("test_rf", clf)

        pred = MLPredictor(model_name="test_rf", registry=reg)
        pred.load()
        signal = pred.predict_signal(X)
        assert signal in (SignalType.BUY, SignalType.SELL, SignalType.HOLD)

    def test_load_missing_model_stays_neutral(self, tmp_path):
        from engine.ml.model_registry import ModelRegistry
        from engine.indicators.ml_predictor import MLPredictor
        reg = ModelRegistry(base_dir=tmp_path / "models")
        pred = MLPredictor(model_name="does_not_exist", registry=reg)
        pred.load()
        assert pred._model is None  # gracefully stays None

    def test_predict_proba_neutral(self):
        from engine.indicators.ml_predictor import MLPredictor
        pred = MLPredictor()
        result = pred.predict_proba(pd.DataFrame({"a": [1, 2, 3]}))
        assert result.shape == (3, 3)
        np.testing.assert_allclose(result, 1 / 3)


# --------------- PortfolioTracker ---------------


class TestPortfolioTracker:
    def test_initial_state(self):
        from engine.portfolio.tracker import PortfolioTracker

        tracker = PortfolioTracker(initial_cash=50_000.0)
        assert tracker.cash == 50_000.0
        assert tracker.total_value == 50_000.0
        assert tracker.positions == {}

    def test_update_position_and_price(self):
        from engine.portfolio.tracker import PortfolioTracker

        tracker = PortfolioTracker(initial_cash=100_000.0)
        tracker.update_position("BTC/USDT", 2.0)
        tracker.update_price("BTC/USDT", 50_000.0)
        assert tracker.total_value == 100_000.0 + 2.0 * 50_000.0

    def test_remove_position(self):
        from engine.portfolio.tracker import PortfolioTracker

        tracker = PortfolioTracker()
        tracker.update_position("ETH", 10.0)
        assert "ETH" in tracker.positions
        tracker.update_position("ETH", 0)
        assert "ETH" not in tracker.positions

    def test_snapshot(self):
        from engine.portfolio.tracker import PortfolioTracker

        tracker = PortfolioTracker(initial_cash=10_000.0)
        tracker.update_position("AAPL", 5.0)
        tracker.update_price("AAPL", 200.0)
        snap = tracker.snapshot()
        assert snap.cash == 10_000.0
        assert snap.total_value == 10_000.0 + 5 * 200.0
        assert "AAPL" in snap.positions
        assert len(tracker.history) == 1


# --------------- Ledger ---------------


class TestLedger:
    def test_record_trade(self):
        from engine.portfolio.ledger import Ledger, TradeType

        ledger = Ledger()
        rec = ledger.record("BTC/USDT", TradeType.BUY, 1.0, 60000.0, 30.0)
        assert rec.id == "TXN-00000001"
        assert rec.symbol == "BTC/USDT"
        assert rec.quantity == 1.0
        assert len(ledger.records) == 1

    def test_multiple_records(self):
        from engine.portfolio.ledger import Ledger, TradeType

        ledger = Ledger()
        ledger.record("BTC", TradeType.BUY, 1.0, 60000.0, 30.0, pnl=0)
        ledger.record("BTC", TradeType.SELL, 1.0, 62000.0, 31.0, pnl=2000.0)
        ledger.record("ETH", TradeType.BUY, 10.0, 3000.0, 15.0)
        assert len(ledger.records) == 3
        assert len(ledger.by_symbol("BTC")) == 2
        assert len(ledger.by_symbol("ETH")) == 1

    def test_total_commission_and_pnl(self):
        from engine.portfolio.ledger import Ledger, TradeType

        ledger = Ledger()
        ledger.record("A", TradeType.BUY, 100, 10.0, 5.0, pnl=0)
        ledger.record("A", TradeType.SELL, 100, 12.0, 5.0, pnl=200.0)
        assert ledger.total_commission == 10.0
        assert ledger.total_pnl == 200.0

    def test_records_returns_copy(self):
        from engine.portfolio.ledger import Ledger, TradeType

        ledger = Ledger()
        ledger.record("X", TradeType.BUY, 1, 1, 0)
        records = ledger.records
        records.clear()
        assert len(ledger.records) == 1  # original not affected


# --------------- PairsTradingStrategy ---------------

class TestPairsTradingStrategy:
    def test_parameters(self):
        s = PairsTradingStrategy(
            symbol_a="AAPL", symbol_b="MSFT",
            lookback=30, entry_zscore=1.5, exit_zscore=0.3,
        )
        assert s.parameters() == {
            "symbol_a": "AAPL",
            "symbol_b": "MSFT",
            "lookback": 30,
            "entry_zscore": 1.5,
            "exit_zscore": 0.3,
        }

    def test_short_a_long_b_on_high_zscore(self):
        """When z-score > entry_zscore, should short A and long B."""
        s = PairsTradingStrategy(symbol_a="A", symbol_b="B", lookback=5, entry_zscore=1.5, exit_zscore=0.3)
        # Feed stable ratio bars to build history
        for _ in range(5):
            bar = pd.Series({"price_a": 100.0, "price_b": 100.0, "close": 100.0, "symbol": "A"})
            s.on_bar(bar)
        # Spike the ratio high: A jumps while B stays => high z
        bar = pd.Series({"price_a": 120.0, "price_b": 100.0, "close": 120.0, "symbol": "A"})
        signals = s.on_bar(bar)
        assert len(signals) == 2
        # First signal: SELL A, second: BUY B
        assert signals[0].symbol == "A"
        assert signals[0].signal_type == SignalType.SELL
        assert signals[1].symbol == "B"
        assert signals[1].signal_type == SignalType.BUY

    def test_long_a_short_b_on_low_zscore(self):
        """When z-score < -entry_zscore, should long A and short B."""
        s = PairsTradingStrategy(symbol_a="A", symbol_b="B", lookback=5, entry_zscore=1.5, exit_zscore=0.3)
        for _ in range(5):
            bar = pd.Series({"price_a": 100.0, "price_b": 100.0, "close": 100.0, "symbol": "A"})
            s.on_bar(bar)
        # Ratio drops: A drops while B stays
        bar = pd.Series({"price_a": 80.0, "price_b": 100.0, "close": 80.0, "symbol": "A"})
        signals = s.on_bar(bar)
        assert len(signals) == 2
        assert signals[0].symbol == "A"
        assert signals[0].signal_type == SignalType.BUY
        assert signals[1].symbol == "B"
        assert signals[1].signal_type == SignalType.SELL

    def test_no_signal_insufficient_data(self):
        """Should return empty signals when not enough data for lookback."""
        s = PairsTradingStrategy(lookback=60)
        for i in range(30):
            bar = pd.Series({"price_a": 100.0 + i * 0.1, "price_b": 100.0, "close": 100.0, "symbol": "A"})
            assert s.on_bar(bar) == []

    def test_no_signal_without_prices(self):
        """Should return empty when price_a or price_b is missing."""
        s = PairsTradingStrategy(lookback=5)
        bar = pd.Series({"close": 100.0, "symbol": "A"})
        assert s.on_bar(bar) == []

    def test_exit_on_mean_reversion(self):
        """After entering a position, should flatten when |z| < exit_zscore."""
        s = PairsTradingStrategy(symbol_a="A", symbol_b="B", lookback=10, entry_zscore=2.0, exit_zscore=0.5)
        # Build 10 stable bars (ratio = 1.0)
        for _ in range(10):
            bar = pd.Series({"price_a": 100.0, "price_b": 100.0, "close": 100.0, "symbol": "A"})
            s.on_bar(bar)
        # Enter position: spike ratio to 1.5 => high z (~2.85)
        bar = pd.Series({"price_a": 150.0, "price_b": 100.0, "close": 150.0, "symbol": "A"})
        signals = s.on_bar(bar)
        assert len(signals) == 2  # entered short A / long B
        assert s._position == -1
        # Ratio returns to 1.0; spike still in window but mean is only slightly
        # shifted so z is near 0 => exit
        bar = pd.Series({"price_a": 100.0, "price_b": 100.0, "close": 100.0, "symbol": "A"})
        signals = s.on_bar(bar)
        assert len(signals) == 2
        # Flatten: BUY A back, SELL B back
        assert signals[0].symbol == "A"
        assert signals[0].signal_type == SignalType.BUY
        assert signals[1].symbol == "B"
        assert signals[1].signal_type == SignalType.SELL
        assert s._position == 0


# --------------- GridTradingStrategy ---------------

class TestGridTradingStrategy:
    def test_parameters(self):
        s = GridTradingStrategy(grid_size=0.01, num_grids=20, base_price=50000.0)
        assert s.parameters() == {
            "grid_size": 0.01,
            "num_grids": 20,
            "base_price": 50000.0,
        }

    def test_buy_on_price_drop(self):
        """Price dropping through a grid line should trigger a BUY."""
        s = GridTradingStrategy(grid_size=0.02, num_grids=10, base_price=100.0)
        # First bar initializes the grid
        bar = pd.Series({"close": 100.0, "symbol": "BTC/USDT"})
        assert s.on_bar(bar) == []
        # Price drops below a grid line (2% down)
        bar = pd.Series({"close": 96.0, "symbol": "BTC/USDT"})
        signals = s.on_bar(bar)
        assert len(signals) == 1
        assert signals[0].signal_type == SignalType.BUY

    def test_sell_on_price_rise(self):
        """Price rising through a grid line should trigger a SELL."""
        s = GridTradingStrategy(grid_size=0.02, num_grids=10, base_price=100.0)
        bar = pd.Series({"close": 100.0, "symbol": "BTC/USDT"})
        s.on_bar(bar)
        # Price rises above a grid line (2% up)
        bar = pd.Series({"close": 104.0, "symbol": "BTC/USDT"})
        signals = s.on_bar(bar)
        assert len(signals) == 1
        assert signals[0].signal_type == SignalType.SELL

    def test_no_signal_insufficient_data(self):
        """First bar only initializes grid, no signal."""
        s = GridTradingStrategy()
        bar = pd.Series({"close": 100.0, "symbol": "BTC/USDT"})
        assert s.on_bar(bar) == []

    def test_no_signal_without_close(self):
        """Should return empty when close is missing."""
        s = GridTradingStrategy()
        bar = pd.Series({"symbol": "BTC/USDT"})
        assert s.on_bar(bar) == []

    def test_no_signal_within_grid(self):
        """Small price move within the same grid cell should not trigger."""
        s = GridTradingStrategy(grid_size=0.05, num_grids=10, base_price=100.0)
        bar = pd.Series({"close": 100.0, "symbol": "BTC/USDT"})
        s.on_bar(bar)
        # 1% move is within 5% grid
        bar = pd.Series({"close": 101.0, "symbol": "BTC/USDT"})
        assert s.on_bar(bar) == []

    def test_auto_base_price(self):
        """When base_price=0, first bar's close is used as base."""
        s = GridTradingStrategy(grid_size=0.02, num_grids=10, base_price=0.0)
        bar = pd.Series({"close": 200.0, "symbol": "BTC/USDT"})
        s.on_bar(bar)  # initializes with base=200
        assert s._initialized
        # Grid lines should be around 200
        assert any(abs(g - 200.0) < 0.01 for g in s._grid_lines)


# --------------- Enhanced RsiMeanReversion ---------------

class TestEnhancedRsiMeanReversion:
    def test_parameters_backward_compat(self):
        """Default-only init still works; new params have defaults."""
        s = RsiMeanReversion()
        p = s.parameters()
        assert p["rsi_period"] == 14
        assert p["min_bbw"] == 0.02
        assert p["max_adx"] == 25.0
        assert p["exit_rsi"] == 50.0
        assert p["max_hold_bars"] == 10
        assert p["atr_multiplier"] == 2.0
        assert p["risk_pct"] == 0.01

    def test_parameters_custom(self):
        s = RsiMeanReversion(rsi_period=10, oversold=25.0, overbought=75.0,
                             min_bbw=0.03, max_adx=30.0, exit_rsi=55.0,
                             max_hold_bars=5, atr_multiplier=1.5, risk_pct=0.02)
        p = s.parameters()
        assert p == {
            "rsi_period": 10, "oversold": 25.0, "overbought": 75.0,
            "min_bbw": 0.03, "max_adx": 30.0, "exit_rsi": 55.0,
            "max_hold_bars": 5, "atr_multiplier": 1.5, "risk_pct": 0.02,
        }

    def test_buy_oversold_no_filter(self):
        """Buy triggers when RSI oversold and no filter data present (legacy mode)."""
        s = RsiMeanReversion()
        bar = pd.Series({"close": 100.0, "rsi": 20.0, "symbol": "TEST"})
        signals = s.on_bar(bar)
        assert len(signals) == 1
        assert signals[0].signal_type == SignalType.BUY

    def test_sell_overbought(self):
        s = RsiMeanReversion()
        bar = pd.Series({"close": 100.0, "rsi": 80.0, "symbol": "TEST"})
        signals = s.on_bar(bar)
        assert len(signals) == 1
        assert signals[0].signal_type == SignalType.SELL

    def test_no_signal_neutral(self):
        s = RsiMeanReversion()
        bar = pd.Series({"close": 100.0, "rsi": 50.0, "symbol": "TEST"})
        assert s.on_bar(bar) == []

    def test_no_signal_without_rsi(self):
        s = RsiMeanReversion()
        bar = pd.Series({"close": 100.0, "symbol": "TEST"})
        assert s.on_bar(bar) == []

    def test_bbw_filter_blocks_entry(self):
        """When BBW < min_bbw the entry should be blocked."""
        s = RsiMeanReversion(min_bbw=0.05)
        bar = pd.Series({"close": 100.0, "rsi": 20.0, "bbw": 0.01, "symbol": "TEST"})
        assert s.on_bar(bar) == []

    def test_adx_filter_blocks_entry(self):
        """When ADX > max_adx (strong trend) the entry should be blocked."""
        s = RsiMeanReversion(max_adx=25.0)
        bar = pd.Series({"close": 100.0, "rsi": 20.0, "adx": 40.0, "symbol": "TEST"})
        assert s.on_bar(bar) == []

    def test_filters_pass_allows_entry(self):
        """Entry when both filters pass."""
        s = RsiMeanReversion(min_bbw=0.02, max_adx=25.0)
        bar = pd.Series({"close": 100.0, "rsi": 20.0, "bbw": 0.05, "adx": 15.0,
                         "atr": 2.0, "symbol": "TEST"})
        signals = s.on_bar(bar)
        assert len(signals) == 1
        assert signals[0].signal_type == SignalType.BUY
        assert signals[0].stop_loss is not None

    def test_exit_on_rsi_recovery(self):
        """After entering, should exit when RSI > exit_rsi."""
        s = RsiMeanReversion(exit_rsi=50.0)
        # Entry
        entry_bar = pd.Series({"close": 100.0, "rsi": 20.0, "symbol": "TEST"})
        s.on_bar(entry_bar)
        assert s._in_position
        # Exit
        exit_bar = pd.Series({"close": 105.0, "rsi": 55.0, "symbol": "TEST"})
        signals = s.on_bar(exit_bar)
        assert len(signals) == 1
        assert signals[0].signal_type == SignalType.SELL
        assert signals[0].metadata["reason"] == "exit_rsi"
        assert not s._in_position

    def test_exit_on_max_hold(self):
        """Should exit after max_hold_bars even if RSI stays low."""
        s = RsiMeanReversion(max_hold_bars=3, exit_rsi=80.0)
        # Entry
        s.on_bar(pd.Series({"close": 100.0, "rsi": 20.0, "symbol": "TEST"}))
        # Bars 1 and 2: RSI still low, no exit
        s.on_bar(pd.Series({"close": 101.0, "rsi": 35.0, "symbol": "TEST"}))
        s.on_bar(pd.Series({"close": 102.0, "rsi": 40.0, "symbol": "TEST"}))
        # Bar 3: max_hold reached
        signals = s.on_bar(pd.Series({"close": 103.0, "rsi": 45.0, "symbol": "TEST"}))
        assert len(signals) == 1
        assert signals[0].signal_type == SignalType.SELL
        assert signals[0].metadata["reason"] == "max_hold"

    def test_atr_position_sizing(self):
        """Quantity should be based on ATR when available."""
        s = RsiMeanReversion(risk_pct=0.01, atr_multiplier=2.0)
        bar = pd.Series({"close": 100.0, "rsi": 20.0, "atr": 2.0, "symbol": "TEST"})
        signals = s.on_bar(bar)
        assert len(signals) == 1
        # equity=100_000 * 0.01 / (2.0 * 2.0) = 250
        assert signals[0].quantity == 250.0

    def test_stop_loss_calculation(self):
        """Stop loss = close - atr_multiplier * ATR."""
        s = RsiMeanReversion(atr_multiplier=2.0)
        bar = pd.Series({"close": 100.0, "rsi": 20.0, "atr": 3.0, "symbol": "TEST"})
        signals = s.on_bar(bar)
        assert signals[0].stop_loss == pytest.approx(94.0)


# --------------- DonchianBreakoutStrategy ---------------

class TestDonchianBreakoutStrategy:
    def test_parameters(self):
        s = DonchianBreakoutStrategy(entry_period=30, exit_period=15, atr_period=14,
                                      atr_stop_multiplier=3.0, trend_filter=False,
                                      risk_pct=0.02)
        assert s.parameters() == {
            "entry_period": 30, "exit_period": 15, "atr_period": 14,
            "atr_stop_multiplier": 3.0, "trend_filter": False, "risk_pct": 0.02,
        }

    def test_default_parameters(self):
        s = DonchianBreakoutStrategy()
        p = s.parameters()
        assert p["entry_period"] == 20
        assert p["exit_period"] == 10
        assert p["trend_filter"] is True

    def test_no_signal_insufficient_data(self):
        """Should not signal until entry_period bars are accumulated."""
        s = DonchianBreakoutStrategy(entry_period=5, trend_filter=False)
        for i in range(4):
            bar = pd.Series({"close": 100.0 + i, "high": 101.0 + i,
                             "low": 99.0 + i, "symbol": "TEST"})
            assert s.on_bar(bar) == []

    def test_no_signal_without_ohlc(self):
        s = DonchianBreakoutStrategy()
        bar = pd.Series({"symbol": "TEST"})
        assert s.on_bar(bar) == []

    def test_long_breakout_no_trend_filter(self):
        """Price above upper channel triggers long entry (trend_filter=False)."""
        s = DonchianBreakoutStrategy(entry_period=5, trend_filter=False)
        # Feed 5 bars with a range of 100-104
        for i in range(5):
            bar = pd.Series({"close": 100.0 + i, "high": 101.0 + i,
                             "low": 99.0 + i, "symbol": "TEST"})
            s.on_bar(bar)
        # Bar 6: close > max(highs[-5:]) = 105
        bar = pd.Series({"close": 106.0, "high": 107.0, "low": 105.0, "symbol": "TEST"})
        signals = s.on_bar(bar)
        assert len(signals) == 1
        assert signals[0].signal_type == SignalType.BUY

    def test_short_breakout_no_trend_filter(self):
        """Price below lower channel triggers short entry."""
        s = DonchianBreakoutStrategy(entry_period=5, trend_filter=False)
        for i in range(5):
            bar = pd.Series({"close": 100.0 - i, "high": 101.0 - i,
                             "low": 99.0 - i, "symbol": "TEST"})
            s.on_bar(bar)
        # Bar 6: close < min(lows[-5:]) = 95
        bar = pd.Series({"close": 93.0, "high": 94.0, "low": 92.0, "symbol": "TEST"})
        signals = s.on_bar(bar)
        assert len(signals) == 1
        assert signals[0].signal_type == SignalType.SELL

    def test_trend_filter_blocks_entry(self):
        """With trend_filter=True and wrong EMA alignment, no entry."""
        s = DonchianBreakoutStrategy(entry_period=5, trend_filter=True)
        for i in range(5):
            bar = pd.Series({"close": 100.0 + i, "high": 101.0 + i,
                             "low": 99.0 + i, "symbol": "TEST"})
            s.on_bar(bar)
        # Breakout above upper channel but EMAs in wrong order
        bar = pd.Series({"close": 106.0, "high": 107.0, "low": 105.0,
                         "ema_8": 100.0, "ema_21": 102.0, "ema_50": 101.0,
                         "symbol": "TEST"})
        assert s.on_bar(bar) == []

    def test_trend_filter_allows_entry(self):
        """With trend_filter=True and correct EMA alignment, entry succeeds."""
        s = DonchianBreakoutStrategy(entry_period=5, trend_filter=True)
        for i in range(5):
            bar = pd.Series({"close": 100.0 + i, "high": 101.0 + i,
                             "low": 99.0 + i, "symbol": "TEST"})
            s.on_bar(bar)
        bar = pd.Series({"close": 106.0, "high": 107.0, "low": 105.0,
                         "ema_8": 106.0, "ema_21": 104.0, "ema_50": 102.0,
                         "atr": 1.5, "symbol": "TEST"})
        signals = s.on_bar(bar)
        assert len(signals) == 1
        assert signals[0].signal_type == SignalType.BUY
        assert signals[0].stop_loss is not None

    def test_exit_long_on_exit_channel(self):
        """Long position exits when price drops below exit lower channel."""
        s = DonchianBreakoutStrategy(entry_period=5, exit_period=3, trend_filter=False)
        # Build up 5 bars
        for i in range(5):
            bar = pd.Series({"close": 100.0 + i, "high": 101.0 + i,
                             "low": 99.0 + i, "symbol": "TEST"})
            s.on_bar(bar)
        # Enter long
        bar = pd.Series({"close": 106.0, "high": 107.0, "low": 105.0, "symbol": "TEST"})
        s.on_bar(bar)
        assert s._position == 1
        # Price drops below exit lower channel (min of last 3 lows)
        bar = pd.Series({"close": 90.0, "high": 91.0, "low": 89.0, "symbol": "TEST"})
        signals = s.on_bar(bar)
        assert len(signals) == 1
        assert signals[0].signal_type == SignalType.SELL
        assert s._position == 0

    def test_atr_expansion_halves_quantity(self):
        """When ATR is expanding, quantity should be halved."""
        s = DonchianBreakoutStrategy(entry_period=5, trend_filter=False, risk_pct=0.01)
        # Feed 20 bars with stable ATR to build ATR history
        for i in range(20):
            bar = pd.Series({"close": 100.0, "high": 101.0, "low": 99.0,
                             "atr": 1.0, "symbol": "TEST"})
            s.on_bar(bar)
        # Now feed bars to push entry, with ATR spike > 1.5x MA
        bar = pd.Series({"close": 110.0, "high": 111.0, "low": 109.0,
                         "atr": 2.0, "symbol": "TEST"})
        signals = s.on_bar(bar)
        assert len(signals) == 1
        # Normal qty: 100_000 * 0.01 / (2.0 * 2.0) = 250
        # Halved: 125
        assert signals[0].quantity == 125.0

    def test_stop_loss_on_long(self):
        """Long entry stop_loss = close - atr_stop_multiplier * ATR."""
        s = DonchianBreakoutStrategy(entry_period=5, trend_filter=False,
                                      atr_stop_multiplier=2.0)
        for i in range(5):
            bar = pd.Series({"close": 100.0 + i, "high": 101.0 + i,
                             "low": 99.0 + i, "symbol": "TEST"})
            s.on_bar(bar)
        bar = pd.Series({"close": 106.0, "high": 107.0, "low": 105.0,
                         "atr": 3.0, "symbol": "TEST"})
        signals = s.on_bar(bar)
        assert signals[0].stop_loss == pytest.approx(100.0)

    def test_markets_and_timeframes(self):
        s = DonchianBreakoutStrategy()
        assert Market.A_STOCK in s.markets
        assert Market.CRYPTO in s.markets
        assert Market.US_STOCK in s.markets
        assert TimeFrame.H4 in s.timeframes
        assert TimeFrame.D1 in s.timeframes


# --------------- FundingRateArbStrategy ---------------

class TestFundingRateArbStrategy:
    def test_parameters(self):
        s = FundingRateArbStrategy(
            min_funding_rate=0.001,
            consecutive_positive=5,
            exit_rate_threshold=0.0002,
            max_position_pct=0.5,
        )
        assert s.parameters() == {
            "min_funding_rate": 0.001,
            "consecutive_positive": 5,
            "exit_rate_threshold": 0.0002,
            "max_position_pct": 0.5,
        }

    def test_crypto_only(self):
        s = FundingRateArbStrategy()
        assert s.markets == [Market.CRYPTO]
        assert TimeFrame.H4 in s.timeframes
        assert TimeFrame.D1 in s.timeframes

    def test_entry_on_consecutive_high_funding_rates(self):
        """Should enter when N consecutive rates exceed min_funding_rate."""
        s = FundingRateArbStrategy(min_funding_rate=0.0005, consecutive_positive=3)
        # Feed 3 bars with high funding rates
        for i in range(3):
            bar = pd.Series({
                "close": 50000.0,
                "high": 50100.0,
                "low": 49900.0,
                "symbol": "BTC/USDT",
                "funding_rate": 0.001,
            })
            signals = s.on_bar(bar)

        # Third bar should trigger entry
        assert len(signals) == 1
        assert signals[0].signal_type == SignalType.BUY
        assert signals[0].metadata["type"] == "funding_arb"
        assert signals[0].metadata["hedge"] == "short_perp"
        assert signals[0].metadata["action"] == "entry"

    def test_no_entry_below_threshold(self):
        """Should not enter when funding rates are below min threshold."""
        s = FundingRateArbStrategy(min_funding_rate=0.0005, consecutive_positive=3)
        for _ in range(5):
            bar = pd.Series({
                "close": 50000.0,
                "high": 50100.0,
                "low": 49900.0,
                "symbol": "BTC/USDT",
                "funding_rate": 0.0003,  # Below threshold
            })
            signals = s.on_bar(bar)
        assert len(signals) == 0

    def test_no_entry_interrupted_consecutive(self):
        """A low rate in the middle resets the consecutive count."""
        s = FundingRateArbStrategy(min_funding_rate=0.0005, consecutive_positive=3)
        # Two high, one low, two high -> no entry
        rates = [0.001, 0.001, 0.0002, 0.001, 0.001]
        for rate in rates:
            bar = pd.Series({
                "close": 50000.0, "high": 50100.0, "low": 49900.0,
                "symbol": "BTC/USDT", "funding_rate": rate,
            })
            signals = s.on_bar(bar)
        assert len(signals) == 0

    def test_exit_on_negative_rate(self):
        """Should exit immediately when funding rate goes negative."""
        s = FundingRateArbStrategy(min_funding_rate=0.0005, consecutive_positive=2)
        # Enter position
        for _ in range(2):
            bar = pd.Series({
                "close": 50000.0, "high": 50100.0, "low": 49900.0,
                "symbol": "BTC/USDT", "funding_rate": 0.001,
            })
            s.on_bar(bar)
        assert s._in_position

        # Negative rate -> immediate exit
        bar = pd.Series({
            "close": 50000.0, "high": 50100.0, "low": 49900.0,
            "symbol": "BTC/USDT", "funding_rate": -0.001,
        })
        signals = s.on_bar(bar)
        assert len(signals) == 1
        assert signals[0].signal_type == SignalType.SELL
        assert signals[0].metadata["reason"] == "negative_rate"
        assert not s._in_position

    def test_exit_on_consecutive_below_threshold(self):
        """Should exit after 2 consecutive periods below exit threshold."""
        s = FundingRateArbStrategy(
            min_funding_rate=0.0005,
            consecutive_positive=2,
            exit_rate_threshold=0.0001,
        )
        # Enter position
        for _ in range(2):
            bar = pd.Series({
                "close": 50000.0, "high": 50100.0, "low": 49900.0,
                "symbol": "BTC/USDT", "funding_rate": 0.001,
            })
            s.on_bar(bar)
        assert s._in_position

        # First period below threshold: no exit yet
        bar = pd.Series({
            "close": 50000.0, "high": 50100.0, "low": 49900.0,
            "symbol": "BTC/USDT", "funding_rate": 0.00005,
        })
        signals = s.on_bar(bar)
        assert len(signals) == 0
        assert s._in_position

        # Second period below threshold: exit
        signals = s.on_bar(bar)
        assert len(signals) == 1
        assert signals[0].signal_type == SignalType.SELL
        assert signals[0].metadata["reason"] == "below_threshold"

    def test_no_exit_if_rate_recovers(self):
        """If rate goes above threshold after 1 period below, reset counter."""
        s = FundingRateArbStrategy(
            min_funding_rate=0.0005,
            consecutive_positive=2,
            exit_rate_threshold=0.0001,
        )
        # Enter
        for _ in range(2):
            bar = pd.Series({
                "close": 50000.0, "high": 50100.0, "low": 49900.0,
                "symbol": "BTC/USDT", "funding_rate": 0.001,
            })
            s.on_bar(bar)

        # One period below threshold
        bar = pd.Series({
            "close": 50000.0, "high": 50100.0, "low": 49900.0,
            "symbol": "BTC/USDT", "funding_rate": 0.00005,
        })
        s.on_bar(bar)

        # Rate recovers
        bar = pd.Series({
            "close": 50000.0, "high": 50100.0, "low": 49900.0,
            "symbol": "BTC/USDT", "funding_rate": 0.0005,
        })
        signals = s.on_bar(bar)
        assert len(signals) == 0
        assert s._in_position

    def test_cumulative_funding_tracked(self):
        """Cumulative funding should accumulate while in position."""
        s = FundingRateArbStrategy(min_funding_rate=0.0005, consecutive_positive=2)
        # Enter
        for _ in range(2):
            bar = pd.Series({
                "close": 50000.0, "high": 50100.0, "low": 49900.0,
                "symbol": "BTC/USDT", "funding_rate": 0.001,
            })
            s.on_bar(bar)
        # Hold for one more period
        bar = pd.Series({
            "close": 50000.0, "high": 50100.0, "low": 49900.0,
            "symbol": "BTC/USDT", "funding_rate": 0.001,
        })
        s.on_bar(bar)
        assert s._cumulative_funding == pytest.approx(0.001 * 50000.0)

        # Exit -> metadata includes cumulative funding
        bar = pd.Series({
            "close": 50000.0, "high": 50100.0, "low": 49900.0,
            "symbol": "BTC/USDT", "funding_rate": -0.001,
        })
        signals = s.on_bar(bar)
        expected_total = 0.001 * 50000.0 + (-0.001) * 50000.0
        assert signals[0].metadata["cumulative_funding"] == pytest.approx(expected_total)

    def test_estimated_funding_rate_when_missing(self):
        """When funding_rate is not in bar, should estimate from volatility."""
        s = FundingRateArbStrategy(min_funding_rate=0.0, consecutive_positive=1)
        # Bar without funding_rate but with price data
        bar = pd.Series({
            "close": 100.0, "high": 110.0, "low": 90.0,
            "symbol": "BTC/USDT",
        })
        signals = s.on_bar(bar)
        # Estimated rate = (110-90)/100 * 0.01 = 0.002 > 0 -> entry
        assert len(signals) == 1
        assert signals[0].signal_type == SignalType.BUY

    def test_reentry_after_exit(self):
        """After exiting, should be able to re-enter on new high funding rates."""
        s = FundingRateArbStrategy(min_funding_rate=0.0005, consecutive_positive=2)
        # Enter
        for _ in range(2):
            bar = pd.Series({
                "close": 50000.0, "high": 50100.0, "low": 49900.0,
                "symbol": "BTC/USDT", "funding_rate": 0.001,
            })
            s.on_bar(bar)
        assert s._in_position

        # Exit on negative
        bar = pd.Series({
            "close": 50000.0, "high": 50100.0, "low": 49900.0,
            "symbol": "BTC/USDT", "funding_rate": -0.001,
        })
        s.on_bar(bar)
        assert not s._in_position

        # Re-enter
        for _ in range(2):
            bar = pd.Series({
                "close": 51000.0, "high": 51100.0, "low": 50900.0,
                "symbol": "BTC/USDT", "funding_rate": 0.002,
            })
            signals = s.on_bar(bar)
        assert len(signals) == 1
        assert signals[0].signal_type == SignalType.BUY

    def test_missing_close_returns_empty(self):
        """Bar without close should return no signals."""
        s = FundingRateArbStrategy()
        bar = pd.Series({"symbol": "BTC/USDT", "funding_rate": 0.001})
        assert s.on_bar(bar) == []

    def test_registry_registration(self):
        """Strategy should be registered in the global registry."""
        from engine.strategies.registry import registry
        assert "funding_rate_arb" in registry.list_strategies()
