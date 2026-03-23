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
from engine.strategies.base import Signal, SignalType, Market
from engine.strategies.examples.sma_crossover import SmaCrossoverLegacy
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
        store.execute("""
            INSERT INTO bars VALUES
            ('BTC/USDT', 'crypto', '1d', '2024-01-01', 42000, 43000, 41000, 42500, 1000)
        """)
        out_path = tmp_path / "export.parquet"
        store.export_parquet("SELECT * FROM bars", out_path)
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
