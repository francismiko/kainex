# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/), and this project adheres to [Semantic Versioning](https://semver.org/).

## [0.1.0] - 2026-03-23

### Added

- **Multi-market data collection** -- Unified collector service supporting A-shares (akshare, baostock), crypto (ccxt), and US stocks (yfinance, finnhub)
- **Multi-timeframe support** -- Tick, 1m, 5m, 15m, 1h, 4h, 1d, 1w timeframes for scalping to position trading
- **Backtest engine** -- High-performance vectorized backtesting with equity curves, Sharpe/Sortino/Calmar ratios, and parameter optimization
- **Paper trading** -- Realistic simulation with slippage model, per-market commission rules (A-share stamp tax, T+1 settlement), and order management
- **Risk management** -- Position sizing limits, drawdown circuit breaker, and max exposure controls
- **6 built-in strategies** -- SMA crossover, dual MA, RSI mean reversion, Bollinger breakout, MACD crossover, and momentum strategies
- **NautilusTrader integration** -- Bridge interface (`KainexStrategy`) for running strategies on the NautilusTrader engine
- **ML-ready infrastructure** -- Feature store and model registry for machine learning model inference
- **Strategy framework** -- `AbstractStrategy` base class with signal generation, parameter management, and strategy registry
- **Technical indicators** -- SMA, EMA, RSI, MACD, Bollinger Bands, and ATR implementations
- **Real-time dashboard** -- React frontend with K-line charts (TradingView Lightweight Charts), portfolio PnL, strategy monitoring, drawdown visualization, and monthly return heatmap
- **WebSocket streaming** -- Real-time market data and strategy signal subscriptions via Socket.IO
- **REST API** -- Full CRUD endpoints for strategies, backtests, portfolio, and market data (FastAPI)
- **DuckDB storage** -- OHLCV bar and tick data storage with Parquet export capability
- **SQLite state store** -- Persistent state and configuration storage
- **Scheduled collection** -- Cron-based intraday and end-of-day data collection jobs
- **Frontend tech stack** -- React 19, Vite, TanStack Router/Query/Table, Zustand, shadcn/ui, Tailwind CSS v4
- **Monorepo structure** -- pnpm workspaces with shared packages (types, UI components, chart utilities, Python data models)
- **Docker Compose** -- Optional infrastructure setup for TimescaleDB and Redis Stack
- **CI pipeline** -- GitHub Actions workflow for Python tests (collector + engine) and frontend checks (lint + typecheck + build)
- **`just` command runner** -- Unified task runner for development, testing, and build commands

[0.1.0]: https://github.com/francismiko/kainex/releases/tag/v0.1.0
