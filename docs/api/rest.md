# REST API Reference

The Kainex Engine API is built with FastAPI and runs on `http://localhost:8001` by default. All endpoints are prefixed with `/api/`.

## Health Check

### `GET /health`

Returns the service health status.

**Response:**

```json
{
  "status": "ok",
  "version": "0.1.0"
}
```

---

## Strategies

Manage strategy configurations.

### `GET /api/strategies/`

List all strategy configurations.

**Response:** `StrategyListItem[]`

```json
[
  {
    "id": "a1b2c3d4e5f6",
    "name": "My SMA Strategy",
    "class_name": "sma_crossover",
    "markets": ["crypto"],
    "timeframes": ["1d", "1h"],
    "status": "stopped",
    "created_at": "2024-01-15T10:00:00Z"
  }
]
```

### `GET /api/strategies/{strategy_id}`

Get a single strategy configuration.

**Response:** `StrategyDetail`

```json
{
  "id": "a1b2c3d4e5f6",
  "name": "My SMA Strategy",
  "class_name": "sma_crossover",
  "markets": ["crypto"],
  "timeframes": ["1d", "1h"],
  "status": "stopped",
  "parameters": {
    "short_window": 10,
    "long_window": 30
  },
  "created_at": "2024-01-15T10:00:00Z",
  "updated_at": "2024-01-16T08:30:00Z"
}
```

### `POST /api/strategies/`

Create a new strategy configuration.

**Request body:**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `name` | `string` | Yes | Display name |
| `class_name` | `string` | Yes | Registered strategy class name |
| `parameters` | `object` | No | Strategy parameters |
| `markets` | `string[]` | No | Target markets |
| `timeframes` | `string[]` | No | Target timeframes |

**Response:** `201 Created` with `StrategyDetail`

### `PUT /api/strategies/{strategy_id}`

Update a strategy configuration.

**Request body:**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `parameters` | `object` | No | Updated parameters |
| `status` | `string` | No | New status |

**Response:** `StrategyDetail`

### `POST /api/strategies/{strategy_id}/start`

Start a strategy (set status to `running`).

**Response:** `StrategyDetail`

### `POST /api/strategies/{strategy_id}/stop`

Stop a strategy (set status to `stopped`).

**Response:** `StrategyDetail`

---

## Backtest

Run backtests and parameter optimization.

### `POST /api/backtest/run`

Run a backtest with specified parameters.

**Request body:**

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `strategy_id` | `string` | -- | Strategy ID or class name |
| `parameters` | `object` | `null` | Override strategy parameters |
| `start_date` | `datetime` | -- | Backtest start date |
| `end_date` | `datetime` | -- | Backtest end date |
| `initial_capital` | `float` | `100000.0` | Starting capital |
| `market` | `string` | `"crypto"` | Market type |
| `symbols` | `string[]` | `["BTC/USDT"]` | Symbols to trade |

**Response:** `BacktestResponse`

```json
{
  "id": "abc123",
  "strategy_id": "sma_crossover",
  "status": "completed",
  "equity_curve": [100000, 100150, 99800, ...],
  "trades": [
    {
      "entry_time": "2024-02-01T00:00:00Z",
      "exit_time": "2024-02-15T00:00:00Z",
      "symbol": "BTC/USDT",
      "side": "buy",
      "entry_price": 42000.0,
      "exit_price": 44500.0,
      "quantity": 1.0,
      "pnl": 2500.0
    }
  ],
  "metrics": {
    "sharpe_ratio": 1.45,
    "sortino_ratio": 2.1,
    "max_drawdown": -0.08,
    "win_rate": 0.62,
    "profit_factor": 1.8,
    "annual_return": 0.35,
    "total_return": 0.28
  },
  "created_at": "2024-03-20T12:00:00Z"
}
```

### `GET /api/backtest/results`

List all backtest results.

**Response:** `BacktestListItem[]`

### `GET /api/backtest/results/{result_id}`

Get a specific backtest result.

**Response:** `BacktestResponse`

### `POST /api/backtest/optimize`

Run a grid search parameter optimization.

**Request body:**

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `strategy_id` | `string` | -- | Strategy ID or class name |
| `param_grid` | `object` | -- | Parameter grid (key: param name, value: list of values) |
| `start_date` | `datetime` | -- | Backtest start date |
| `end_date` | `datetime` | -- | Backtest end date |
| `initial_capital` | `float` | `100000.0` | Starting capital |
| `market` | `string` | `"crypto"` | Market type |
| `symbols` | `string[]` | `["BTC/USDT"]` | Symbols to trade |
| `metric` | `string` | `"sharpe_ratio"` | Metric to optimize |

**Response:** `OptimizeResponse`

```json
{
  "results": [
    {
      "parameters": {"short_window": 10, "long_window": 30},
      "metrics": {"sharpe_ratio": 1.45, ...},
      "rank": 1
    },
    {
      "parameters": {"short_window": 5, "long_window": 50},
      "metrics": {"sharpe_ratio": 1.20, ...},
      "rank": 2
    }
  ],
  "best_parameters": {"short_window": 10, "long_window": 30},
  "total_combinations": 12
}
```

---

## Portfolio

View portfolio state, positions, trades, and performance.

### `GET /api/portfolio/summary`

Get the current portfolio summary.

**Response:** `PortfolioSummary`

```json
{
  "total_value": 105000.0,
  "cash": 50000.0,
  "positions": [
    {
      "symbol": "BTC/USDT",
      "market": "crypto",
      "side": "long",
      "quantity": 0.5,
      "entry_price": 42000.0,
      "current_price": 44000.0,
      "unrealized_pnl": 1000.0
    }
  ],
  "total_pnl": 5000.0,
  "daily_pnl": 250.0
}
```

### `GET /api/portfolio/positions`

List all open positions.

**Response:** `PositionItem[]`

### `GET /api/portfolio/trades`

List trade history.

**Query parameters:**

| Param | Type | Default | Description |
|-------|------|---------|-------------|
| `offset` | `int` | `0` | Pagination offset |
| `limit` | `int` | `50` | Max results (1-500) |

**Response:** `TradeRecord[]`

```json
[
  {
    "id": "trade_001",
    "strategy": "sma_crossover",
    "symbol": "BTC/USDT",
    "market": "crypto",
    "side": "buy",
    "price": 42000.0,
    "quantity": 0.5,
    "commission": 4.2,
    "pnl": 500.0,
    "timestamp": "2024-03-15T14:30:00Z"
  }
]
```

### `GET /api/portfolio/performance`

Get aggregated performance metrics.

**Response:** `PerformanceMetrics`

```json
{
  "sharpe_ratio": 1.45,
  "sortino_ratio": 2.1,
  "max_drawdown": -0.08,
  "win_rate": 0.62,
  "profit_factor": 1.8,
  "annual_return": 0.35,
  "total_return": 0.28,
  "total_trades": 42
}
```

### `POST /api/portfolio/trades/{trade_id}/notes`

Create a trade note (for the trade journal).

**Request body:**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `content` | `string` | Yes | Note content |

**Response:** `201 Created` with `TradeNote`

### `GET /api/portfolio/trades/{trade_id}/notes`

List notes for a specific trade.

**Response:** `TradeNote[]`

---

## Market Data

Query market data from DuckDB.

### `GET /api/market-data/bars`

Get OHLCV bar data.

**Query parameters:**

| Param | Type | Default | Description |
|-------|------|---------|-------------|
| `symbol` | `string` | -- | Trading pair symbol (required) |
| `market` | `string` | `"crypto"` | Market type |
| `timeframe` | `string` | `"1d"` | Bar timeframe |
| `start` | `datetime` | `null` | Start time filter |
| `end` | `datetime` | `null` | End time filter |
| `limit` | `int` | `100` | Max bars (1-5000) |

**Response:** `BarData[]`

```json
[
  {
    "symbol": "BTC/USDT",
    "market": "crypto",
    "timeframe": "1d",
    "open": 42000.0,
    "high": 43500.0,
    "low": 41800.0,
    "close": 43200.0,
    "volume": 15000.0,
    "timestamp": "2024-03-15T00:00:00Z"
  }
]
```

### `GET /api/market-data/latest`

Get latest quotes for one or more symbols.

**Query parameters:**

| Param | Type | Default | Description |
|-------|------|---------|-------------|
| `symbols` | `string` | `"BTC/USDT"` | Comma-separated symbols |
| `market` | `string` | `"crypto"` | Market type |

**Response:** `LatestQuote[]`

### `GET /api/market-data/symbols`

List all available symbols for a market.

**Query parameters:**

| Param | Type | Default | Description |
|-------|------|---------|-------------|
| `market` | `string` | `"crypto"` | Market type |

**Response:** `SymbolInfo[]`

### `GET /api/market-data/status`

Get data quality status for each market.

**Response:** `MarketDataStatusResponse`

```json
{
  "markets": [
    {
      "market": "crypto",
      "symbols": ["BTC/USDT", "ETH/USDT"],
      "total_bars": 15000,
      "latest_bar_time": "2024-03-20T00:00:00Z",
      "staleness_seconds": 86400.0,
      "has_gaps": false
    }
  ],
  "total_bars": 15000,
  "duckdb_size_mb": 12.5
}
```

---

## Alerts

Manage price alerts.

### `POST /api/alerts`

Create a price alert.

**Request body:**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `symbol` | `string` | Yes | Symbol to watch |
| `market` | `string` | Yes | Market type |
| `condition` | `string` | Yes | Alert condition (`above`, `below`, etc.) |
| `price` | `float` | Yes | Trigger price |
| `message` | `string` | No | Custom alert message |

**Response:** `201 Created` with `AlertItem`

### `GET /api/alerts`

List all alerts.

**Response:** `AlertItem[]`

### `PATCH /api/alerts/{alert_id}`

Update an alert.

**Response:** `AlertItem`

### `DELETE /api/alerts/{alert_id}`

Delete an alert.

**Response:** `204 No Content`

---

## Logs

Query execution logs.

### `GET /api/logs/`

List log entries.

**Query parameters:**

| Param | Type | Default | Description |
|-------|------|---------|-------------|
| `level` | `string` | `null` | Filter by level (`INFO`, `WARNING`, `ERROR`) |
| `strategy_id` | `string` | `null` | Filter by strategy source |
| `limit` | `int` | `100` | Max entries (1-1000) |
| `offset` | `int` | `0` | Pagination offset |

**Response:** `LogEntry[]`

```json
[
  {
    "timestamp": "2024-03-20T14:30:00Z",
    "level": "INFO",
    "source": "sma_crossover",
    "message": "BUY signal generated for BTC/USDT at 42000.0",
    "metadata": null
  }
]
```

### `GET /api/logs/strategies/{strategy_id}`

List logs for a specific strategy.

**Query parameters:** Same as `GET /api/logs/` (except `strategy_id`).

**Response:** `LogEntry[]`
