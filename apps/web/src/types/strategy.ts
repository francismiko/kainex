export type StrategyStatus = 'running' | 'stopped' | 'error'

export interface Strategy {
  id: string
  name: string
  description: string
  status: StrategyStatus
  market: string
  symbols: string[]
  pnl: number
  createdAt: string
  updatedAt: string
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
  symbol: string
  side: 'buy' | 'sell'
  price: number
  quantity: number
  pnl: number
  timestamp: string
}

export interface BacktestResult {
  equity_curve: { time: string; value: number }[]
  trades: BacktestTrade[]
  metrics: BacktestMetrics
}
