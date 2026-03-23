# Kainex

![License](https://img.shields.io/github/license/francismiko/kainex)
![Python](https://img.shields.io/badge/Python-3.12-blue)
![React](https://img.shields.io/badge/React-19-blue)
![Tests](https://img.shields.io/badge/Tests-202%20passing-green)

> The edge you engineer. -- Open-source multi-market quantitative trading platform.

Kainex is an open-source quantitative trading platform supporting A-shares, crypto, and US stocks with strategy backtesting, paper trading, and real-time monitoring.

Kainex 是一个开源的多市场量化交易平台，支持 A 股、加密货币和美股的策略回测、模拟交易与实时监控。

## Features

- **Multi-market support** -- Unified interface for A-shares (via akshare/baostock), crypto (via ccxt), and US stocks (via yfinance/finnhub)
- **Multi-timeframe** -- Tick, 1m, 5m, 15m, 1h, 4h, 1d, 1w -- from scalping to position trading
- **Backtest engine** -- High-performance vectorized backtesting with equity curves, Sharpe/Sortino/Calmar ratios, and parameter optimization
- **Paper trading** -- Realistic simulation with slippage model, per-market commission rules (A-share stamp tax, T+1), and order management
- **Risk management** -- Position sizing limits, drawdown circuit breaker, max exposure controls
- **9 built-in strategies** -- SMA crossover, dual MA, RSI mean reversion, Bollinger breakout, MACD crossover, momentum, ML signal, pairs trading, grid trading -- all ready to extend
- **Parameter optimization** -- Grid search API with heatmap UI visualization, ranked by Sharpe/return/win rate
- **NautilusTrader integration** -- Bridge interface (`KainexStrategy`) for running strategies on the NautilusTrader engine
- **ML pipeline** -- Feature store (25+ features), model registry (versioned), training script with RandomForest example
- **Technical indicators overlay** -- SMA, EMA, Bollinger Bands, RSI, MACD, Volume -- overlaid on K-line charts
- **Strategy comparison** -- Side-by-side backtest comparison with equity curve overlay
- **Real-time dashboard** -- K-line charts (TradingView Lightweight Charts), portfolio PnL, strategy monitoring, drawdown visualization, monthly return heatmap
- **WebSocket real-time streaming** -- Market data, strategy signals, portfolio updates, and execution logs
- **Watchlist sidebar** -- Customizable symbol watchlist with real-time price updates
- **Price alert system** -- Configurable price alerts with notification support
- **Real-time execution logs** -- Live streaming log viewer for strategy execution and system events
- **Trade journal** -- Trade notes and K-line annotations for post-trade analysis
- **CSV export** -- Export backtest results and trade history to CSV
- **Command+K search** -- Global keyboard shortcut for quick navigation and search
- **Animated numbers** -- Smooth number transitions for real-time price and PnL updates
- **Responsive mobile layout** -- Mobile-friendly responsive design across all pages
- **Settings page** -- Theme toggle (light/dark) and color scheme customization
- **Data management page** -- Data source status, storage usage, and import/export controls
- **REST API** -- Full CRUD for strategies, backtests, portfolio, market data, alerts, and logs
- **OpenAPI TypeScript generation** -- Auto-generated TypeScript types from OpenAPI schema
- **Portless integration** -- Seamless service discovery without hardcoded ports
- **launchd background service** -- macOS launchd plist for running collector as a background daemon
- **Smoke test + Playwright E2E** -- Smoke test script and end-to-end browser tests (202 tests: 186 unit + 16 E2E)

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
just e2e          # Run Playwright E2E tests
just smoke-test   # Run smoke test health checks
just seed         # Seed database with sample data
just build        # Build frontend
just lint         # Lint frontend
just typecheck    # Type check frontend
just install-service   # Install launchd background service
just uninstall-service # Uninstall launchd background service
```

## Project Structure

```
kainex/
├── apps/web/                   # React frontend (Vite + TanStack)
│   ├── src/
│   │   ├── components/         # UI components (charts, layout, strategy, trading, shared)
│   │   ├── routes/             # File-based routing
│   │   │   ├── market/         # Market data & K-line charts
│   │   │   ├── portfolio/      # Portfolio PnL & positions
│   │   │   ├── risk/           # Risk dashboard & drawdown
│   │   │   ├── strategies/     # Strategy CRUD & comparison
│   │   │   ├── trades/         # Trade journal & annotations
│   │   │   ├── alerts/         # Price alert management
│   │   │   ├── logs/           # Real-time execution logs
│   │   │   ├── settings/       # Theme & color scheme settings
│   │   │   └── data/           # Data management & import/export
│   │   ├── hooks/              # Custom hooks (API, WebSocket)
│   │   ├── stores/             # Zustand state management
│   │   └── types/              # TypeScript type definitions
│   └── e2e/                    # Playwright E2E tests
├── packages/
│   ├── shared/                 # Shared Python data models (kainex-shared)
│   ├── types/                  # Shared TypeScript types
│   ├── ui/                     # Shared UI components
│   └── chart-utils/            # Chart utility functions
├── scripts/                    # Operational scripts
│   ├── install-launchd.sh      # Install macOS launchd service
│   ├── uninstall-launchd.sh    # Uninstall launchd service
│   ├── smoke_test.sh           # Smoke test health checks
│   └── com.kainex.collector.plist  # launchd plist definition
├── services/
│   ├── collector/              # Market data collection service
│   │   └── src/collector/
│   │       ├── models/         # Bar, Tick, Market, TimeFrame (from kainex-shared)
│   │       ├── sources/        # Data source adapters (astock, crypto, us_stock, baostock, finnhub)
│   │       ├── storage/        # DuckDB writer + Parquet export
│   │       └── jobs/           # Scheduled collection jobs (intraday, EOD)
│   └── engine/                 # Strategy engine + API service
│       └── src/engine/
│           ├── api/            # FastAPI routes (backtest, strategies, portfolio, market-data, alerts, logs, websocket)
│           ├── core/           # Backtest engine, strategy runner, parameter optimizer
│           ├── strategies/     # Strategy framework + 9 example strategies
│           ├── paper_trading/  # Paper broker, slippage model, commission rules
│           ├── portfolio/      # Position tracker, PnL ledger, performance calculator
│           ├── risk/           # Risk manager, drawdown circuit breaker, position limiter
│           ├── indicators/     # Technical indicators (SMA, EMA, RSI, MACD, BBands, ATR)
│           ├── ml/             # Feature store, model registry, training pipeline
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
