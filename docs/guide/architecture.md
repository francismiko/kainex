# Architecture

Kainex follows a three-layer architecture: a React frontend, a FastAPI engine service, and a Python collector service, all sharing a DuckDB data store.

## System Overview

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

## Data Flow

1. **Collector** fetches OHLCV data from external sources (akshare, baostock, ccxt, yfinance, finnhub) on a scheduled basis.
2. Data is written into **DuckDB** and optionally exported as **Parquet** files.
3. The **Engine** reads historical data from DuckDB for backtesting and paper trading.
4. The **Frontend** communicates with the Engine via REST API for CRUD operations and WebSocket for real-time streaming.

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

## Project Structure

```
kainex/
├── apps/web/                   # React frontend (Vite + TanStack)
│   ├── src/
│   │   ├── components/         # UI components (charts, layout, strategy, trading, shared)
│   │   ├── routes/             # File-based routing (market, portfolio, risk, strategies, ...)
│   │   ├── hooks/              # Custom hooks (API, WebSocket)
│   │   ├── stores/             # Zustand state management
│   │   └── types/              # TypeScript type definitions
│   └── e2e/                    # Playwright E2E tests
├── packages/
│   ├── shared/                 # Shared Python data models (kainex-shared)
│   ├── types/                  # Shared TypeScript types
│   ├── ui/                     # Shared UI components
│   └── chart-utils/            # Chart utility functions
├── scripts/                    # Operational scripts (launchd, smoke test)
├── services/
│   ├── collector/              # Market data collection service
│   │   └── src/collector/
│   │       ├── models/         # Bar, Tick, Market, TimeFrame
│   │       ├── sources/        # Data source adapters (astock, crypto, us_stock, baostock, finnhub)
│   │       ├── storage/        # DuckDB writer + Parquet export
│   │       └── jobs/           # Scheduled collection jobs (intraday, EOD)
│   └── engine/                 # Strategy engine + API service
│       └── src/engine/
│           ├── api/            # FastAPI routes + schemas
│           ├── core/           # Backtest engine, strategy runner, parameter optimizer
│           ├── strategies/     # Strategy framework + 9 example strategies
│           ├── paper_trading/  # Paper broker, slippage model, commission rules
│           ├── portfolio/      # Position tracker, PnL ledger, performance calculator
│           ├── risk/           # Risk manager, drawdown circuit breaker, position limiter
│           ├── indicators/     # Technical indicators (SMA, EMA, RSI, MACD, BBands, ATR)
│           ├── ml/             # Feature store, model registry, training pipeline
│           └── storage/        # DuckDB store, SQLite store
└── docker/                     # Docker Compose (optional TimescaleDB + Redis)
```

## Module Responsibilities

### Collector Service

Handles all data ingestion. Each market has its own source adapter:

- **astock** -- A-shares via akshare
- **baostock** -- A-shares historical via baostock
- **crypto** -- Crypto via ccxt (Binance, OKX, etc.)
- **us_stock** -- US stocks via yfinance
- **finnhub** -- US stocks real-time via finnhub

Jobs are scheduled via an async cron scheduler with both intraday and end-of-day collection tasks.

### Engine Service

The core of the platform, responsible for:

- **Strategy Registry** -- Discovers and manages strategy classes
- **Backtest Engine** -- Vectorized backtesting with configurable initial capital and market-specific rules
- **Paper Broker** -- Simulated order execution with slippage and commission models
- **Risk Manager** -- Position sizing limits, drawdown circuit breakers, max exposure controls
- **ML Pipeline** -- Feature store (25+ features), model registry, and prediction pipeline
- **NautilusTrader Bridge** -- `KainexStrategy` adapter for running strategies on the NautilusTrader engine
- **REST API** -- Full CRUD for strategies, backtests, portfolio, market data, alerts, and logs
- **WebSocket** -- Real-time streaming for market data, signals, portfolio updates, and execution logs

### Frontend

A React 19 SPA with file-based routing:

- **Market** -- K-line charts with technical indicator overlays
- **Strategies** -- Strategy CRUD, backtest runner, parameter optimization with heatmap
- **Portfolio** -- Positions, PnL, performance metrics
- **Risk** -- Drawdown visualization, monthly return heatmap
- **Trades** -- Trade journal with annotations
- **Alerts** -- Price alert management
- **Logs** -- Real-time execution log viewer
- **Settings** -- Theme and color scheme customization
- **Data** -- Data management and import/export
