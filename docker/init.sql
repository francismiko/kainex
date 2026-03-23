-- Kainex database initialization
-- Run once after TimescaleDB is up

CREATE EXTENSION IF NOT EXISTS timescaledb;

-- OHLCV bars table
CREATE TABLE IF NOT EXISTS bars (
  symbol     TEXT        NOT NULL,
  market     TEXT        NOT NULL,
  timeframe  TEXT        NOT NULL,
  open       DOUBLE PRECISION NOT NULL,
  high       DOUBLE PRECISION NOT NULL,
  low        DOUBLE PRECISION NOT NULL,
  close      DOUBLE PRECISION NOT NULL,
  volume     DOUBLE PRECISION NOT NULL,
  ts         TIMESTAMPTZ NOT NULL,
  UNIQUE (symbol, market, timeframe, ts)
);

SELECT create_hypertable('bars', by_range('ts'), if_not_exists => TRUE);

-- Create indexes for common queries
CREATE INDEX IF NOT EXISTS idx_bars_symbol_market ON bars (symbol, market, timeframe, ts DESC);

-- Tick data table
CREATE TABLE IF NOT EXISTS ticks (
  symbol TEXT            NOT NULL,
  market TEXT            NOT NULL,
  price  DOUBLE PRECISION NOT NULL,
  volume DOUBLE PRECISION NOT NULL,
  bid    DOUBLE PRECISION NOT NULL,
  ask    DOUBLE PRECISION NOT NULL,
  ts     TIMESTAMPTZ     NOT NULL
);

SELECT create_hypertable('ticks', by_range('ts'), if_not_exists => TRUE);

CREATE INDEX IF NOT EXISTS idx_ticks_symbol ON ticks (symbol, market, ts DESC);

-- Trades table (paper trading records)
CREATE TABLE IF NOT EXISTS trades (
  id         BIGSERIAL PRIMARY KEY,
  strategy   TEXT            NOT NULL,
  symbol     TEXT            NOT NULL,
  market     TEXT            NOT NULL,
  side       TEXT            NOT NULL, -- buy/sell
  price      DOUBLE PRECISION NOT NULL,
  quantity   DOUBLE PRECISION NOT NULL,
  commission DOUBLE PRECISION NOT NULL DEFAULT 0,
  slippage   DOUBLE PRECISION NOT NULL DEFAULT 0,
  pnl        DOUBLE PRECISION,
  ts         TIMESTAMPTZ     NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_trades_strategy ON trades (strategy, ts DESC);

-- Positions table
CREATE TABLE IF NOT EXISTS positions (
  id         BIGSERIAL PRIMARY KEY,
  strategy   TEXT            NOT NULL,
  symbol     TEXT            NOT NULL,
  market     TEXT            NOT NULL,
  side       TEXT            NOT NULL, -- long/short
  quantity   DOUBLE PRECISION NOT NULL,
  entry_price DOUBLE PRECISION NOT NULL,
  current_price DOUBLE PRECISION,
  unrealized_pnl DOUBLE PRECISION,
  opened_at  TIMESTAMPTZ     NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ     NOT NULL DEFAULT NOW(),
  UNIQUE (strategy, symbol, market, side)
);

-- Strategy configurations
CREATE TABLE IF NOT EXISTS strategy_configs (
  id          TEXT PRIMARY KEY,
  name        TEXT NOT NULL,
  class_name  TEXT NOT NULL,
  parameters  JSONB NOT NULL DEFAULT '{}',
  markets     JSONB NOT NULL DEFAULT '[]',
  timeframes  JSONB NOT NULL DEFAULT '[]',
  status      TEXT NOT NULL DEFAULT 'stopped', -- running/stopped/backtest
  created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Backtest results
CREATE TABLE IF NOT EXISTS backtest_results (
  id            BIGSERIAL PRIMARY KEY,
  strategy_id   TEXT NOT NULL,
  parameters    JSONB NOT NULL,
  start_date    TIMESTAMPTZ NOT NULL,
  end_date      TIMESTAMPTZ NOT NULL,
  equity_curve  JSONB,
  metrics       JSONB NOT NULL, -- sharpe, sortino, max_drawdown, etc.
  trades_count  INT NOT NULL DEFAULT 0,
  created_at    TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_backtest_strategy ON backtest_results (strategy_id, created_at DESC);

-- Continuous aggregate for daily bars from intraday
CREATE MATERIALIZED VIEW IF NOT EXISTS bars_daily
WITH (timescaledb.continuous) AS
SELECT
  symbol,
  market,
  time_bucket('1 day', ts) AS bucket,
  first(open, ts) AS open,
  max(high) AS high,
  min(low) AS low,
  last(close, ts) AS close,
  sum(volume) AS volume
FROM bars
WHERE timeframe IN ('1m', '5m', '15m', '1h')
GROUP BY symbol, market, time_bucket('1 day', ts)
WITH NO DATA;
