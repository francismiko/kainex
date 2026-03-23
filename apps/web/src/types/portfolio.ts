export type PositionSide = 'long' | 'short'

export interface Position {
  id: string
  symbol: string
  side: PositionSide
  quantity: number
  entryPrice: number
  currentPrice: number
  unrealizedPnl: number
  strategyId: string
}

export type TradeStatus = 'filled' | 'partial' | 'cancelled'

export interface Trade {
  id: string
  symbol: string
  side: 'buy' | 'sell'
  price: number
  quantity: number
  status: TradeStatus
  strategyId: string
  timestamp: string
}

export interface Portfolio {
  totalValue: number
  cash: number
  positions: Position[]
  dailyPnl: number
  totalPnl: number
}
