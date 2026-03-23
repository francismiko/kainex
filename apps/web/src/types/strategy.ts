export type StrategyStatus = 'running' | 'stopped' | 'error'

export interface Strategy {
  id: string
  name: string
  class_name: string
  description: string
  status: StrategyStatus
  market: string
  markets: string[]
  symbols: string[]
  timeframes: string[]
  parameters: Record<string, unknown>
  pnl: number
  createdAt: string
  updatedAt: string
}

export interface StrategyCreateInput {
  name: string
  class_name: string
  parameters?: Record<string, unknown>
  markets: string[]
  timeframes: string[]
}

export type SignalDirection = 'long' | 'short' | 'close'

export interface Signal {
  id: string
  strategyId: string
  symbol: string
  direction: SignalDirection
  price: number
  quantity: number
  timestamp: string
}

export interface BacktestMetrics {
  sharpe: number
  sortino: number
  max_drawdown: number
  win_rate: number
  profit_factor: number
  annual_return: number
  total_return: number
  trade_count: number
}

export interface BacktestTrade {
  id: string
  entry_time: string
  exit_time?: string
  symbol: string
  side: 'buy' | 'sell'
  entry_price: number
  exit_price?: number
  price: number
  quantity: number
  pnl: number
  timestamp: string
}

export interface BacktestResult {
  id?: string
  strategy_id?: string
  status?: string
  equity_curve: { time: string; value: number }[]
  trades: BacktestTrade[]
  metrics: BacktestMetrics
}

export interface OptimizeResultItem {
  parameters: Record<string, unknown>
  metrics: BacktestMetrics
  rank: number
}

export interface OptimizeResponse {
  results: OptimizeResultItem[]
  best_parameters: Record<string, unknown>
  total_combinations: number
}
