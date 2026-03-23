# Configuration

Kainex uses a combination of environment variables, Python configuration, and a justfile for managing settings and commands.

## Environment Variables

Create a `.env` file at the project root or in each service directory. Environment variables are loaded automatically by the services.

### Engine Service

| Variable | Default | Description |
|----------|---------|-------------|
| `KAINEX_ENGINE_HOST` | `0.0.0.0` | Engine API bind address |
| `KAINEX_ENGINE_PORT` | `8001` | Engine API port |
| `KAINEX_DUCKDB_PATH` | `data/kainex.duckdb` | Path to DuckDB database |
| `KAINEX_SQLITE_PATH` | `data/kainex.sqlite` | Path to SQLite database |
| `KAINEX_CORS_ORIGINS` | `http://localhost:5173` | Allowed CORS origins (comma-separated) |

### Collector Service

| Variable | Default | Description |
|----------|---------|-------------|
| `KAINEX_COLLECTOR_INTERVAL` | `60` | Collection interval in seconds |
| `KAINEX_DUCKDB_PATH` | `data/kainex.duckdb` | Path to DuckDB database |
| `FINNHUB_API_KEY` | -- | Finnhub API key for US stock data |

### Frontend

| Variable | Default | Description |
|----------|---------|-------------|
| `VITE_API_BASE_URL` | `http://localhost:8001` | Engine API base URL |
| `VITE_WS_URL` | `ws://localhost:8001/api/ws/stream` | WebSocket endpoint |

## Storage Configuration

### DuckDB

DuckDB is the primary store for OHLCV market data. The database file is shared between the Collector (write) and Engine (read) services. By default it lives at `data/kainex.duckdb` relative to the project root.

Collected data can also be exported as Parquet files for external analysis.

### SQLite

SQLite stores application state: strategy configurations, backtest results, trade ledger, alerts, and trade notes. Default path: `data/kainex.sqlite`.

### Optional Infrastructure

For production deployments, you can use Docker Compose to spin up:

- **TimescaleDB** -- Time-series database for high-frequency tick data
- **Redis Stack** -- Caching and pub/sub for real-time data distribution

```bash
cd docker
docker compose up -d
```

## Justfile Commands

The [justfile](https://github.com/casey/just) at the project root serves as the unified command runner. Run `just` to see all available commands:

### Development

| Command | Description |
|---------|-------------|
| `just dev` | Start all services with Portless |
| `just dev-plain` | Start all services with plain ports |
| `just web` | Start frontend only |
| `just collector` | Start collector only |
| `just engine` | Start engine API only |
| `just proxy` | Start Portless proxy |

### Build & Quality

| Command | Description |
|---------|-------------|
| `just build` | Build frontend |
| `just lint` | Lint frontend |
| `just typecheck` | TypeScript type check |
| `just generate-types` | Generate TS types from OpenAPI spec |

### Testing

| Command | Description |
|---------|-------------|
| `just py-test` | Run Python unit tests |
| `just e2e` | Run Playwright E2E tests |
| `just smoke-test` | Run smoke test health checks |

### Data & Services

| Command | Description |
|---------|-------------|
| `just seed` | Seed database with sample data |
| `just py-install` | Install Python dependencies |
| `just install-service` | Install collector as macOS launchd daemon |
| `just uninstall-service` | Uninstall launchd daemon |
| `just service-status` | Check launchd service status |

## Launchd Background Service

On macOS, the collector can run as a launchd daemon that starts automatically on login:

```bash
# Install the service
just install-service

# Check status
just service-status

# Uninstall
just uninstall-service
```

The launchd plist is defined in `scripts/com.kainex.collector.plist`.

## Portless Integration

Kainex uses [Portless](https://github.com/nicolo-ribaudo/portless) for semantic local URLs during development:

- `http://kainex.localhost:1355` -- Frontend
- `http://api.kainex.localhost:1355` -- Engine API

Start the proxy once with `just proxy`, then use `just dev` which automatically wraps services with Portless.
