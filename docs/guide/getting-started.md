# Getting Started

Kainex is an open-source quantitative trading platform supporting A-shares, crypto, and US stocks with strategy backtesting, paper trading, and real-time monitoring.

## Prerequisites

- **Node.js 22+** and **pnpm 9+**
- **Python 3.12+** and [uv](https://docs.astral.sh/uv/)
- [just](https://github.com/casey/just) (command runner)
- **Docker** (optional, for TimescaleDB/Redis)

## Installation

```bash
git clone https://github.com/francismiko/kainex.git
cd kainex

# Install all dependencies (pnpm + uv)
just setup
```

This runs `pnpm install` for the frontend/TypeScript packages and `uv sync` for each Python service.

## Running Services

Start all services with a single command:

```bash
just dev
```

This launches:

| Service     | URL                                   |
|-------------|---------------------------------------|
| Frontend    | `http://kainex.localhost:1355`         |
| Engine API  | `http://api.kainex.localhost:1355`     |
| Collector   | Background process                    |

If you prefer plain ports without Portless:

```bash
just dev-plain
```

This starts the frontend on `http://localhost:5173` and the engine API on `http://localhost:8001`.

### Running Individual Services

```bash
just web          # Frontend only
just collector    # Collector only
just engine       # Engine API only
```

## Seeding Sample Data

Populate the database with sample market data for development:

```bash
just seed
```

## Testing

```bash
just py-test      # Run Python unit tests
just e2e          # Run Playwright E2E tests
just smoke-test   # Run smoke test health checks
```

## Available Commands

Run `just` with no arguments to see all commands:

```bash
just              # List all commands
just dev          # Start all services
just web          # Frontend only
just collector    # Collector service
just engine       # Engine API
just py-test      # Python tests
just e2e          # Playwright E2E tests
just smoke-test   # Smoke test health checks
just seed         # Seed sample data
just build        # Build frontend
just lint         # Lint frontend
just typecheck    # TypeScript type checking
just generate-types    # Generate TS types from OpenAPI
just install-service   # Install launchd background service
just uninstall-service # Uninstall launchd service
```

## Next Steps

- Read the [Architecture](/guide/architecture) overview to understand how the system is structured.
- Explore the [Configuration](/guide/configuration) guide to customize your setup.
- Check out the [Built-in Strategies](/strategies/built-in) to start backtesting.
