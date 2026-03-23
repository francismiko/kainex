# Custom Strategy Development

This guide walks through creating, registering, and testing a custom strategy in Kainex.

## Step 1: Create the Strategy File

Create a new Python file in `services/engine/src/engine/strategies/examples/`:

```python
# services/engine/src/engine/strategies/examples/my_strategy.py
import pandas as pd

from engine.strategies.base import (
    AbstractStrategy,
    Market,
    Signal,
    SignalType,
    TimeFrame,
)
from engine.strategies.registry import registry


@registry.register
class MyStrategy(AbstractStrategy):
    """Custom strategy description."""

    name = "my_strategy"
    description = "Buy/sell based on custom logic"
    timeframes = [TimeFrame.D1]
    markets = [Market.CRYPTO]

    def __init__(self, param_a: float = 1.0, param_b: int = 20) -> None:
        self.param_a = param_a
        self.param_b = param_b
        self.warmup_periods = param_b

    def on_bar(self, bar: pd.Series) -> list[Signal]:
        close = bar.get("close")
        if close is None:
            return []

        signals: list[Signal] = []

        # Your signal logic here
        if some_buy_condition:
            signals.append(
                Signal(
                    symbol=bar.get("symbol", ""),
                    signal_type=SignalType.BUY,
                    price=close,
                    quantity=1.0,
                    stop_loss=close * 0.95,  # optional
                )
            )

        return signals

    def parameters(self) -> dict:
        return {
            "param_a": self.param_a,
            "param_b": self.param_b,
        }
```

## Step 2: Register the Strategy

The `@registry.register` decorator automatically registers the strategy class. To ensure it is imported at startup, add an import in the strategies init file:

```python
# services/engine/src/engine/strategies/__init__.py
"""Strategy framework."""

from engine.strategies.examples import sma_crossover as _  # noqa: F401
from engine.strategies.examples import my_strategy as _my  # noqa: F401  # [!code ++]
```

Alternatively, the registry will pick it up if the module is imported anywhere during application startup.

## Step 3: Use Pre-Computed Indicators

The backtest engine can attach indicator columns to each bar before passing it to `on_bar()`. Common indicators available in the bar Series:

| Column | Description |
|--------|-------------|
| `open`, `high`, `low`, `close`, `volume` | OHLCV data |
| `sma_short`, `sma_long` | Simple moving averages |
| `ma_fast`, `ma_slow` | Moving averages (EMA or SMA) |
| `rsi` | Relative Strength Index |
| `macd`, `macd_signal` | MACD line and signal line |
| `bb_upper`, `bb_lower`, `bb_middle` | Bollinger Bands |
| `atr` | Average True Range |
| `symbol` | Asset symbol |
| `timestamp` | Bar timestamp |

You can also compute your own indicators within the strategy by maintaining internal state (as the SMA Crossover NautilusTrader variant does with its `_closes` buffer).

## Step 4: NautilusTrader Integration

For advanced strategies requiring order management, portfolio tracking, or multi-instrument logic, use the `KainexStrategy` base class:

```python
from nautilus_trader.model.data import Bar
from engine.strategies.base import (
    KainexStrategy,
    KainexStrategyConfig,
    Signal,
    SignalType,
    TimeFrame,
    Market,
)
from engine.strategies.registry import registry


class MyAdvancedConfig(KainexStrategyConfig, frozen=True):
    fast_window: int = 5
    slow_window: int = 20


class MyAdvancedStrategy(KainexStrategy):
    """Advanced strategy using NautilusTrader."""

    name = "my_advanced"
    description = "Advanced strategy with NautilusTrader engine"
    timeframes = [TimeFrame.H1, TimeFrame.D1]
    markets = [Market.CRYPTO]

    def __init__(self, config: MyAdvancedConfig | None = None) -> None:
        if config is None:
            config = MyAdvancedConfig()
        super().__init__(config)
        self._closes: list[float] = []

    def on_kainex_bar(self, bar: Bar) -> list[Signal]:
        self._closes.append(float(bar.close))

        if len(self._closes) < self._config.slow_window:
            return []

        # Your logic with NautilusTrader Bar
        fast_avg = sum(self._closes[-self._config.fast_window:]) / self._config.fast_window
        slow_avg = sum(self._closes[-self._config.slow_window:]) / self._config.slow_window

        signals: list[Signal] = []
        if fast_avg > slow_avg:
            signals.append(
                Signal(
                    symbol=str(bar.bar_type.instrument_id),
                    signal_type=SignalType.BUY,
                    price=float(bar.close),
                    quantity=1.0,
                )
            )
        return signals

    def kainex_parameters(self) -> dict:
        return {
            "fast_window": self._config.fast_window,
            "slow_window": self._config.slow_window,
        }
```

## Step 5: Backtest via API

Once registered, your strategy is available through the REST API:

```bash
# Run a backtest
curl -X POST http://localhost:8001/api/backtest/run \
  -H "Content-Type: application/json" \
  -d '{
    "strategy_id": "my_strategy",
    "parameters": {"param_a": 1.5, "param_b": 30},
    "start_date": "2024-01-01T00:00:00Z",
    "end_date": "2024-12-31T00:00:00Z",
    "initial_capital": 100000,
    "market": "crypto",
    "symbols": ["BTC/USDT"]
  }'
```

## Step 6: Parameter Optimization

Search for optimal parameters using the grid search API:

```bash
curl -X POST http://localhost:8001/api/backtest/optimize \
  -H "Content-Type: application/json" \
  -d '{
    "strategy_id": "my_strategy",
    "param_grid": {
      "param_a": [0.5, 1.0, 1.5, 2.0],
      "param_b": [10, 20, 30, 50]
    },
    "start_date": "2024-01-01T00:00:00Z",
    "end_date": "2024-12-31T00:00:00Z",
    "metric": "sharpe_ratio"
  }'
```

The response includes all parameter combinations ranked by the chosen metric (Sharpe ratio, total return, win rate, etc.).

## Step 7: Testing

Write unit tests for your strategy:

```python
# services/engine/tests/strategies/test_my_strategy.py
import pandas as pd
import pytest

from engine.strategies.examples.my_strategy import MyStrategy


def test_buy_signal():
    strategy = MyStrategy(param_a=1.0, param_b=5)
    # Feed warmup bars
    for i in range(5):
        bar = pd.Series({"close": 100 + i, "symbol": "BTC/USDT"})
        strategy.on_bar(bar)

    # Feed bar that should trigger buy
    bar = pd.Series({"close": 110, "symbol": "BTC/USDT"})
    signals = strategy.on_bar(bar)
    assert len(signals) == 1
    assert signals[0].signal_type == SignalType.BUY


def test_parameters():
    strategy = MyStrategy(param_a=2.0, param_b=30)
    assert strategy.parameters() == {"param_a": 2.0, "param_b": 30}
```

Run tests:

```bash
cd services/engine && uv run pytest tests/strategies/test_my_strategy.py
```

## Tips

- **Warmup period:** Set `warmup_periods` to the minimum number of bars your strategy needs before it can generate valid signals. The backtest engine skips signal evaluation during warmup.
- **Stop loss:** Use the `stop_loss` field on `Signal` to set per-trade risk limits. The paper broker respects these.
- **Multiple signals:** A single `on_bar()` call can return multiple signals (useful for pairs trading or portfolio rebalancing).
- **State management:** Store intermediate state as instance variables. The strategy instance persists across bars within a single backtest run.
- **Feature engineering:** For ML-based strategies, use the `FeatureStore` to compute a rich feature set from raw OHLCV data.
