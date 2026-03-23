import { useEffect, useRef, useState, useSyncExternalStore } from 'react'
import {
  acquire,
  release,
  subscribe,
  unsubscribe,
  addMessageHandler,
  subscribeToState,
  getConnectionState,
  type ConnectionState,
} from '@/lib/websocket'

// --------------- Connection status ---------------

/**
 * Returns the current WebSocket connection state: 'connecting' | 'connected' | 'disconnected'.
 */
export function useConnectionStatus(): ConnectionState {
  return useSyncExternalStore(subscribeToState, getConnectionState)
}

// --------------- Generic channel hook ---------------

/**
 * Low-level hook: subscribe to a channel, receive the latest message data.
 * Manages acquire/release and subscribe/unsubscribe lifecycle.
 */
function useChannel<T>(channel: string | null): T | null {
  const [data, setData] = useState<T | null>(null)
  const channelRef = useRef(channel)

  useEffect(() => {
    channelRef.current = channel
    if (!channel) return

    acquire()
    subscribe(channel)

    const removeHandler = addMessageHandler((ch, payload) => {
      if (ch === channelRef.current) {
        setData(payload as T)
      }
    })

    return () => {
      removeHandler()
      unsubscribe(channel)
      release()
      setData(null)
    }
  }, [channel])

  return data
}

// --------------- Market stream ---------------

export interface MarketBar {
  symbol: string
  timeframe: string
  open: number
  high: number
  low: number
  close: number
  volume: number
  timestamp: number
}

export interface MarketStreamResult {
  /** Latest bar received from the WebSocket */
  latestBar: MarketBar | null
  /** Connection state */
  status: ConnectionState
}

/**
 * Subscribe to real-time market data for a symbol + timeframe.
 * Channel format: `market:{symbol}:{timeframe}`
 */
export function useMarketStream(
  symbol: string | null,
  timeframe: string | null,
): MarketStreamResult {
  const channel =
    symbol && timeframe ? `market:${symbol}:${timeframe}` : null
  const latestBar = useChannel<MarketBar>(channel)
  const status = useConnectionStatus()
  return { latestBar, status }
}

// --------------- Signal stream ---------------

export interface StrategySignal {
  strategy_id: string
  symbol: string
  direction: 'long' | 'short' | 'close'
  price: number
  quantity: number
  timestamp: number
}

export interface SignalStreamResult {
  /** Latest signal received from the WebSocket */
  latestSignal: StrategySignal | null
  /** All signals accumulated during this subscription */
  signals: StrategySignal[]
  /** Connection state */
  status: ConnectionState
}

/**
 * Subscribe to strategy signals.
 * Channel format: `signals:{strategy_id}`
 */
export function useSignalStream(strategyId: string | null): SignalStreamResult {
  const channel = strategyId ? `signals:${strategyId}` : null
  const [signals, setSignals] = useState<StrategySignal[]>([])
  const [latestSignal, setLatestSignal] = useState<StrategySignal | null>(null)
  const channelRef = useRef(channel)
  const status = useConnectionStatus()

  useEffect(() => {
    channelRef.current = channel
    if (!channel) return

    acquire()
    subscribe(channel)
    // eslint-disable-next-line -- reset state on channel change is intentional
    setSignals([]); setLatestSignal(null)

    const removeHandler = addMessageHandler((ch, payload) => {
      if (ch === channelRef.current) {
        const sig = payload as StrategySignal
        setLatestSignal(sig)
        setSignals((prev) => [...prev.slice(-99), sig])
      }
    })

    return () => {
      removeHandler()
      unsubscribe(channel)
      release()
    }
  }, [channel])

  return { latestSignal, signals, status }
}

// --------------- Portfolio stream ---------------

export interface PortfolioSnapshot {
  total_value: number
  cash: number
  daily_pnl: number
  total_pnl: number
  positions_count: number
  timestamp: number
}

export interface PortfolioStreamResult {
  /** Latest portfolio snapshot from the WebSocket */
  portfolio: PortfolioSnapshot | null
  /** Connection state */
  status: ConnectionState
}

/**
 * Subscribe to real-time portfolio updates.
 * Channel: `portfolio`
 */
export function usePortfolioStream(): PortfolioStreamResult {
  const portfolio = useChannel<PortfolioSnapshot>('portfolio')
  const status = useConnectionStatus()
  return { portfolio, status }
}

// --------------- Log stream ---------------

export interface LogEntry {
  timestamp: string
  level: string
  source: string
  message: string
  metadata: Record<string, unknown> | null
}

export interface LogStreamResult {
  /** All log entries accumulated during this subscription */
  logs: LogEntry[]
  /** Connection state */
  status: ConnectionState
}

/**
 * Subscribe to real-time log entries.
 * Channel: `logs`
 */
export function useLogStream(): LogStreamResult {
  const [logs, setLogs] = useState<LogEntry[]>([])
  const status = useConnectionStatus()

  useEffect(() => {
    acquire()
    subscribe('logs')
    setLogs([])

    const removeHandler = addMessageHandler((ch, payload) => {
      if (ch === 'logs') {
        const entry = payload as LogEntry
        setLogs((prev) => [...prev.slice(-999), entry])
      }
    })

    return () => {
      removeHandler()
      unsubscribe('logs')
      release()
    }
  }, [])

  return { logs, status }
}

// --------------- Helper: convert WebSocket bar to lightweight-charts candlestick ---------------

/**
 * Convert a MarketBar from the WebSocket into a lightweight-charts CandlestickData-like object.
 */
export function barToCandlestick(bar: MarketBar): {
  time: number
  open: number
  high: number
  low: number
  close: number
} {
  return {
    time: bar.timestamp,
    open: bar.open,
    high: bar.high,
    low: bar.low,
    close: bar.close,
  }
}
