# Strategy Development Overview

Kainex provides a flexible strategy framework with two interfaces: a legacy bar-by-bar `AbstractStrategy` and a NautilusTrader-powered `KainexStrategy`. Both produce the same `Signal` output and can be backtested through the same engine.

## Strategy Interfaces

### AbstractStrategy (Legacy)

The simpler interface for bar-by-bar signal generation. Each call to `on_bar()` receives a pandas Series with pre-computed indicators and returns a list of signals.

```python
from engine.strategies.base import AbstractStrategy, Signal, SignalType, TimeFrame, Market

class MyStrategy(AbstractStrategy):
    name = "my_strategy"
    description = "My custom strategy"
    timeframes = [TimeFrame.D1]
    markets = [Market.CRYPTO]
    warmup_periods = 20

    def __init__(self, threshold: float = 0.02):
        self.threshold = threshold

    def on_bar(self, bar: pd.Series) -> list[Signal]:
        # Your logic here
        return []

    def parameters(self) -> dict:
        return {"threshold": self.threshold}
```

### KainexStrategy (NautilusTrader)

For strategies that need the full power of the NautilusTrader engine. Subclass `KainexStrategy` and implement `on_kainex_bar()`:

```python
from engine.strategies.base import KainexStrategy, KainexStrategyConfig

class MyNautilusStrategy(KainexStrategy):
    name = "my_nautilus_strategy"
    description = "NautilusTrader-powered strategy"
    timeframes = [TimeFrame.D1, TimeFrame.H1]
    markets = [Market.CRYPTO]

    def __init__(self, config: MyConfig | None = None):
        if config is None:
            config = MyConfig()
        super().__init__(config)

    def on_kainex_bar(self, bar: Bar) -> list[Signal]:
        # Process NautilusTrader Bar
        return []

    def kainex_parameters(self) -> dict:
        return {}
```

## Signal Model

Both interfaces produce `Signal` objects:

| Field | Type | Description |
|-------|------|-------------|
| `symbol` | `str` | Trading pair (e.g., `BTC/USDT`) |
| `signal_type` | `SignalType` | `BUY` or `SELL` |
| `price` | `float` | Signal price |
| `quantity` | `float` | Order quantity |
| `stop_loss` | `float \| None` | Optional stop-loss price |

## Supported Markets and Timeframes

### Markets

| Market | Enum | Data Sources |
|--------|------|-------------|
| A-Shares | `Market.A_STOCK` | akshare, baostock |
| Crypto | `Market.CRYPTO` | ccxt (Binance, OKX, etc.) |
| US Stocks | `Market.US_STOCK` | yfinance, finnhub |

### Timeframes

| Timeframe | Enum | Typical Use |
|-----------|------|-------------|
| 1 minute | `TimeFrame.M1` | Scalping, grid trading |
| 5 minutes | `TimeFrame.M5` | Short-term |
| 15 minutes | `TimeFrame.M15` | Intraday |
| 1 hour | `TimeFrame.H1` | Swing trading |
| 4 hours | `TimeFrame.H4` | Multi-day |
| 1 day | `TimeFrame.D1` | Position trading |
| 1 week | `TimeFrame.W1` | Long-term |

## Strategy Registry

Strategies are registered using the `@registry.register` decorator. Once registered, they are discoverable through the REST API and can be used in backtesting and paper trading.

```python
from engine.strategies.registry import registry

@registry.register
class MyStrategy(AbstractStrategy):
    ...
```

## Backtesting

Run a backtest via the API:

```bash
curl -X POST http://localhost:8001/api/backtest/run \
  -H "Content-Type: application/json" \
  -d '{
    "strategy_id": "sma_crossover",
    "start_date": "2024-01-01T00:00:00Z",
    "end_date": "2024-12-31T00:00:00Z",
    "initial_capital": 100000,
    "market": "crypto",
    "symbols": ["BTC/USDT"]
  }'
```

The response includes equity curve, trade list, and performance metrics (Sharpe ratio, Sortino ratio, max drawdown, win rate, etc.).

## Parameter Optimization

Use the grid search API to find optimal parameters:

```bash
curl -X POST http://localhost:8001/api/backtest/optimize \
  -H "Content-Type: application/json" \
  -d '{
    "strategy_id": "sma_crossover",
    "param_grid": {
      "short_window": [5, 10, 15, 20],
      "long_window": [20, 30, 50]
    },
    "start_date": "2024-01-01T00:00:00Z",
    "end_date": "2024-12-31T00:00:00Z",
    "metric": "sharpe_ratio"
  }'
```

Results are ranked by the chosen metric, and the frontend provides heatmap visualization for two-parameter grids.
