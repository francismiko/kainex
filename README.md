# Kainex

> The edge you engineer. — 多市场量化交易平台

开源的多市场量化交易平台，支持 A 股、加密货币和美股的模拟盘交易、策略回测与实时监控。

## Features

- **多市场支持** — A 股、加密货币、美股统一接入
- **多时间框架** — 超短线、短线、中线、长线策略全覆盖
- **回测引擎** — 基于 VectorBT 的高性能向量化回测
- **模拟交易** — 真实滑点/手续费模型的纸上交易
- **风控系统** — 仓位限制、回撤熔断、敞口控制
- **可视化看板** — 实时 K 线、PnL 曲线、策略监控
- **ML 就绪** — 内置机器学习模型推理接口

## Tech Stack

| Layer | Stack |
|-------|-------|
| Strategy Engine | Python, FastAPI, VectorBT, pandas-ta |
| Data Collection | akshare (A-stocks), ccxt (crypto), yfinance (US stocks) |
| Frontend | React 19, Vite, TanStack Router/Query, shadcn/ui |
| Charts | TradingView Lightweight Charts, Apache ECharts |
| Database | TimescaleDB (PostgreSQL), Redis Stack |
| Infra | Docker Compose, Turborepo, uv |

## Quick Start

```bash
# Prerequisites: Node.js 22+, pnpm, Python 3.12+, uv, Docker

# Clone and setup
git clone https://github.com/francismiko/kainex.git
cd kainex
just setup

# Start development
just dev
```

## Project Structure

```
kainex/
├── apps/web/              # React frontend
├── packages/              # Shared TS packages
├── services/
│   ├── collector/         # Market data collection (Python)
│   └── engine/            # Strategy engine + API (Python)
└── docker/                # Infrastructure configs
```

## License

[MIT](LICENSE)
