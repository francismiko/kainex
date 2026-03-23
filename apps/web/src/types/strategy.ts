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
