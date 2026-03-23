export const Market = {
  A_STOCK: 'a_stock',
  CRYPTO: 'crypto',
  US_STOCK: 'us_stock',
} as const
export type Market = (typeof Market)[keyof typeof Market]

export const TimeFrame = {
  TICK: 'tick',
  M1: '1m',
  M5: '5m',
  M15: '15m',
  H1: '1h',
  H4: '4h',
  D1: '1d',
  W1: '1w',
} as const
export type TimeFrame = (typeof TimeFrame)[keyof typeof TimeFrame]

export interface Bar {
  symbol: string
  market: Market
  timeframe: TimeFrame
  open: number
  high: number
  low: number
  close: number
  volume: number
  timestamp: string
}

export interface Tick {
  symbol: string
  market: Market
  price: number
  volume: number
  timestamp: string
}
