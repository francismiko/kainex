# Kainex

> The edge you engineer. -- Open-source multi-market quantitative trading platform.

Kainex is an open-source quantitative trading platform supporting A-shares, crypto, and US stocks with strategy backtesting, paper trading, and real-time monitoring.

Kainex 是一个开源的多市场量化交易平台，支持 A 股、加密货币和美股的策略回测、模拟交易与实时监控。

## Features

- **Multi-market support** -- Unified interface for A-shares (via akshare/baostock), crypto (via ccxt), and US stocks (via yfinance/finnhub)
- **Multi-timeframe** -- Tick, 1m, 5m, 15m, 1h, 4h, 1d, 1w -- from scalping to position trading
- **Backtest engine** -- High-performance vectorized backtesting with equity curves, Sharpe/Sortino/Calmar ratios, and parameter optimization
- **Paper trading** -- Realistic simulation with slippage model, per-market commission rules (A-share stamp tax, T+1), and order management
- **Risk management** -- Position sizing limits, drawdown circuit breaker, max exposure controls
- **6 built-in strategies** -- SMA crossover, dual MA, RSI mean reversion, Bollinger breakout, MACD crossover, momentum -- all ready to extend
- **NautilusTrader integration** -- Bridge interface (`KainexStrategy`) for running strategies on the NautilusTrader engine
- **ML-ready** -- Feature store and model registry for machine learning model inference
- **Real-time dashboard** -- K-line charts (TradingView Lightweight Charts), portfolio PnL, strategy monitoring, drawdown visualization, monthly return heatmap
- **WebSocket streaming** -- Real-time market data and strategy signal subscriptions
- **REST API** -- Full CRUD for strategies, backtests, portfolio, and market data

## Tech Stack

| Layer | Stack |
|-------|-------|
| Strategy Engine | Python 3.12, FastAPI, NautilusTrader, pandas-ta |
| Data Collection | akshare, baostock (A-shares), ccxt (crypto), yfinance, finnhub (US stocks) |
| Frontend | React 19, Vite, TanStack Router/Query/Table, Zustand, shadcn/ui |
| Charts | TradingView Lightweight Charts, Apache ECharts |
| Storage | DuckDB (OHLCV data + Parquet export), SQLite (state + configs) |
| Infra (optional) | TimescaleDB, Redis Stack, Docker Compose |
| Tooling | pnpm, uv, just, Tailwind CSS v4, TypeScript 5.9 |

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     React Frontend (Vite)                   │
│  K-line Charts │ Strategy CRUD │ Portfolio │ Risk Dashboard  │
└────────┬───────────────────────────────┬────────────────────┘
         │  REST API                     │  WebSocket
         ▼                               ▼
┌─────────────────────────────────────────────────────────────┐
│                  Engine Service (FastAPI)                    │
│  Backtest Engine │ Paper Broker │ Risk Manager │ Scheduler   │
│  Strategy Registry │ NautilusTrader Bridge │ ML Predictor    │
└────────┬────────────────────────────────────────────────────┘
         │  DuckDB (read)
         ▼
┌─────────────────────────────────────────────────────────────┐
│                 Collector Service (Python)                   │
│  akshare │ baostock │ ccxt │ yfinance │ finnhub             │
│  DuckDB Writer │ Parquet Export │ Scheduler                  │
└─────────────────────────────────────────────────────────────┘
         │
         ▼
    ┌──────────┐
    │  DuckDB  │  OHLCV bars + ticks
    └──────────┘
```

## Quick Start

### Prerequisites

- Node.js 22+, pnpm 9+
- Python 3.12+, [uv](https://docs.astral.sh/uv/)
- [just](https://github.com/casey/just) (command runner)
- Docker (optional, for TimescaleDB/Redis)

### Setup

```bash
git clone https://github.com/francismiko/kainex.git
cd kainex

# Install all dependencies (pnpm + uv)
just setup

# Start all services (frontend + collector + engine)
just dev
```

The frontend will be available at `http://localhost:5173` and the engine API at `http://localhost:8001`.

### Available Commands

```bash
just              # List all commands
just dev          # Start all services
just web          # Frontend only
just collector    # Collector only
just engine       # Engine API only
just py-test      # Run Python tests
just build        # Build frontend
just lint         # Lint frontend
just typecheck    # Type check frontend
```

## Project Structure

```
kainex/
├── apps/web/                   # React frontend (Vite + TanStack)
│   └── src/
│       ├── components/         # UI components (charts, layout, strategy)
│       ├── routes/             # File-based routing (market, portfolio, risk, strategies, trades)
│       ├── hooks/              # Custom hooks (API, WebSocket)
│       ├── stores/             # Zustand state management
│       └── types/              # TypeScript type definitions
├── packages/
│   ├── shared/                 # Shared Python data models (kainex-shared)
│   ├── types/                  # Shared TypeScript types
│   ├── ui/                     # Shared UI components
│   └── chart-utils/            # Chart utility functions
├── services/
│   ├── collector/              # Market data collection service
│   │   └── src/collector/
│   │       ├── models/         # Bar, Tick, Market, TimeFrame (from kainex-shared)
│   │       ├── sources/        # Data source adapters (astock, crypto, us_stock, baostock, finnhub)
│   │       ├── storage/        # DuckDB writer + Parquet export
│   │       └── jobs/           # Scheduled collection jobs (intraday, EOD)
│   └── engine/                 # Strategy engine + API service
│       └── src/engine/
│           ├── api/            # FastAPI routes (backtest, strategies, portfolio, market-data, websocket)
│           ├── core/           # Backtest engine, strategy runner, parameter optimizer
│           ├── strategies/     # Strategy framework + 6 example strategies
│           ├── paper_trading/  # Paper broker, slippage model, commission rules
│           ├── portfolio/      # Position tracker, PnL ledger, performance calculator
│           ├── risk/           # Risk manager, drawdown circuit breaker, position limiter
│           ├── indicators/     # Technical indicators (SMA, EMA, RSI, MACD, BBands, ATR)
│           ├── ml/             # Feature store, model registry
│           ├── storage/        # DuckDB store, SQLite store
│           └── scheduler.py    # Async cron scheduler
└── docker/                     # Docker Compose (optional TimescaleDB + Redis)
```

## Strategy Development

Create a new strategy by subclassing `AbstractStrategy`:

```python
from engine.strategies.base import AbstractStrategy, Signal, SignalType
import pandas as pd


class MyStrategy(AbstractStrategy):
    name = "my_strategy"
    description = "My custom strategy"
    timeframes = [TimeFrame.D1]
    markets = [Market.CRYPTO]
    warmup_periods = 20

    def __init__(self, threshold: float = 0.02):
        self.threshold = threshold

    def on_bar(self, bar: pd.Series) -> list[Signal]:
        # Your signal logic here
        if some_condition:
            return [Signal(
                symbol=bar["symbol"],
                signal_type=SignalType.BUY,
                price=bar["close"],
                quantity=1.0,
                stop_loss=bar["close"] * 0.95,
            )]
        return []

    def parameters(self) -> dict:
        return {"threshold": self.threshold}
```

Register it in `engine/strategies/examples/` and import it in `engine/strategies/__init__.py` to make it available via the API.

For NautilusTrader-powered strategies, subclass `KainexStrategy` instead:

```python
from engine.strategies.base import KainexStrategy, KainexStrategyConfig

class MyNautilusStrategy(KainexStrategy):
    def on_kainex_bar(self, bar: Bar) -> list[Signal]:
        # NautilusTrader bar processing
        ...
```

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feat/my-feature`)
3. Make your changes and add tests
4. Run tests: `just py-test`
5. Commit your changes (`git commit -m 'feat: add my feature'`)
6. Push to the branch (`git push origin feat/my-feature`)
7. Open a Pull Request

## License

[MIT](LICENSE)
