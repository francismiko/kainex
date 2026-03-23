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
- **9 built-in strategies** -- SMA crossover, dual MA, RSI mean reversion, Bollinger breakout, MACD crossover, momentum, ML signal, pairs trading, and grid trading
- **NautilusTrader integration** -- Bridge interface (`KainexStrategy`) for running strategies on the NautilusTrader engine
- **ML pipeline** -- Feature store (25+ features), model registry (versioned artifacts), and training script with RandomForest example
- **Strategy framework** -- `AbstractStrategy` base class with signal generation, parameter management, and strategy registry
- **Technical indicators overlay** -- SMA, EMA, Bollinger Bands, RSI, MACD, and Volume overlaid on K-line charts
- **Real-time dashboard** -- React frontend with K-line charts (TradingView Lightweight Charts), portfolio PnL, strategy monitoring, drawdown visualization, and monthly return heatmap
- **Parameter optimization API** -- Grid search endpoint with heatmap UI visualization, ranked by Sharpe/return/win rate
- **WebSocket real-time streaming** -- Market data, strategy signals, portfolio updates, and execution logs via Socket.IO
- **Strategy comparison page** -- Side-by-side backtest comparison with equity curve overlay
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
- **REST API** -- Full CRUD endpoints for strategies, backtests, portfolio, market data, alerts, and logs (FastAPI)
- **OpenAPI TypeScript generation** -- Auto-generated TypeScript types from OpenAPI schema
- **Portless integration** -- Seamless service discovery without hardcoded ports
- **DuckDB storage** -- OHLCV bar and tick data storage with Parquet export capability
- **SQLite state store** -- Persistent state and configuration storage
- **Scheduled collection** -- Cron-based intraday and end-of-day data collection jobs
- **launchd background service** -- macOS launchd plist for running collector as a background daemon
- **Frontend tech stack** -- React 19, Vite, TanStack Router/Query/Table, Zustand, shadcn/ui, Tailwind CSS v4
- **Monorepo structure** -- pnpm workspaces with shared packages (types, UI components, chart utilities, Python data models)
- **Docker Compose** -- Optional infrastructure setup for TimescaleDB and Redis Stack
- **CI pipeline** -- GitHub Actions workflow for Python tests (collector + engine) and frontend checks (lint + typecheck + build)
- **Smoke test** -- Quick validation script for service health checks
- **Playwright E2E tests** -- End-to-end browser tests for dashboard, market, and navigation flows
- **`just` command runner** -- Unified task runner for development, testing, and build commands

[0.1.0]: https://github.com/francismiko/kainex/releases/tag/v0.1.0
