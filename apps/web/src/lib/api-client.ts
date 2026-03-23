import type { Strategy, StrategyCreateInput, BacktestResult, OptimizeResponse } from '@/types/strategy'
import type { Portfolio, Position, Trade } from '@/types/portfolio'
import type { Bar } from '@/types/market'

const API_BASE = import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8001'

export async function apiFetch<T>(
  path: string,
  options?: RequestInit,
): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    headers: { 'Content-Type': 'application/json', ...options?.headers },
    ...options,
  })
  if (!res.ok) {
    const text = await res.text().catch(() => '')
    throw new Error(text || `API error: ${res.status} ${res.statusText}`)
  }
  return res.json() as Promise<T>
}

/* eslint-disable @typescript-eslint/no-explicit-any */
function mapStrategy(raw: any): Strategy {
  return {
    id: raw.id,
    name: raw.name,
    class_name: raw.class_name ?? '',
    description: raw.description ?? '',
    status: raw.status ?? 'stopped',
    market: (raw.markets ?? [])[0] ?? '',
    markets: raw.markets ?? [],
    symbols: raw.symbols ?? [],
    timeframes: raw.timeframes ?? [],
    parameters: raw.parameters ?? {},
    pnl: raw.performance?.total_return ?? raw.pnl ?? 0,
    createdAt: raw.created_at ?? '',
    updatedAt: raw.updated_at ?? '',
  }
}

function mapBacktestResult(raw: any): BacktestResult {
  const equityCurve = (raw.equity_curve ?? []).map((v: any, i: number) => {
    if (typeof v === 'number') return { time: String(i), value: v }
    return { time: v.time ?? String(i), value: v.value ?? v }
  })
  const trades = (raw.trades ?? []).map((t: any) => ({
    id: t.id ?? `${t.entry_time}-${t.symbol}`,
    entry_time: t.entry_time ?? '',
    exit_time: t.exit_time ?? undefined,
    symbol: t.symbol ?? '',
    side: t.side ?? 'buy',
    entry_price: t.entry_price ?? 0,
    exit_price: t.exit_price ?? undefined,
    price: t.entry_price ?? t.price ?? 0,
    quantity: t.quantity ?? 0,
    pnl: t.pnl ?? 0,
    timestamp: t.entry_time ?? t.timestamp ?? '',
  }))
  const m = raw.metrics ?? {}
  return {
    id: raw.id,
    strategy_id: raw.strategy_id,
    status: raw.status,
    equity_curve: equityCurve,
    trades,
    metrics: {
      sharpe: m.sharpe_ratio ?? m.sharpe ?? 0,
      sortino: m.sortino_ratio ?? m.sortino ?? 0,
      max_drawdown: m.max_drawdown ?? 0,
      win_rate: m.win_rate ?? 0,
      profit_factor: m.profit_factor ?? 0,
      annual_return: m.annual_return ?? 0,
      total_return: m.total_return ?? 0,
      trade_count: m.trade_count ?? trades.length,
    },
  }
}
/* eslint-enable @typescript-eslint/no-explicit-any */

export const api = {
  strategies: {
    list: async () => {
      const raw = await apiFetch<unknown[]>('/api/strategies')
      return raw.map(mapStrategy)
    },
    get: async (id: string) => {
      const raw = await apiFetch<unknown>(`/api/strategies/${id}`)
      return mapStrategy(raw)
    },
    create: async (data: StrategyCreateInput) => {
      const raw = await apiFetch<unknown>('/api/strategies', {
        method: 'POST',
        body: JSON.stringify(data),
      })
      return mapStrategy(raw)
    },
    delete: (id: string) =>
      apiFetch<void>(`/api/strategies/${id}`, { method: 'DELETE' }),
    start: async (id: string) => {
      const raw = await apiFetch<unknown>(`/api/strategies/${id}/start`, { method: 'POST' })
      return mapStrategy(raw)
    },
    stop: async (id: string) => {
      const raw = await apiFetch<unknown>(`/api/strategies/${id}/stop`, { method: 'POST' })
      return mapStrategy(raw)
    },
  },
  backtest: {
    run: async (data: {
      strategy_id: string
      start_date: string
      end_date: string
      initial_capital: number
      market?: string
      symbols?: string[]
    }) => {
      const raw = await apiFetch<unknown>('/api/backtest/run', {
        method: 'POST',
        body: JSON.stringify(data),
      })
      return mapBacktestResult(raw)
    },
    results: async () => {
      const raw = await apiFetch<unknown[]>('/api/backtest/results')
      return raw.map(mapBacktestResult)
    },
    result: async (id: string) => {
      const raw = await apiFetch<unknown>(`/api/backtest/results/${id}`)
      return mapBacktestResult(raw)
    },
    optimize: async (data: {
      strategy_id: string
      param_grid: Record<string, number[]>
      start_date: string
      end_date: string
      initial_capital: number
      market?: string
      symbols?: string[]
      metric?: string
    }) => {
      return apiFetch<OptimizeResponse>('/api/backtest/optimize', {
        method: 'POST',
        body: JSON.stringify(data),
      })
    },
  },
  portfolio: {
    summary: () => apiFetch<Portfolio>('/api/portfolio/summary'),
    positions: () => apiFetch<Position[]>('/api/portfolio/positions'),
    trades: (page?: number) =>
      apiFetch<Trade[]>(`/api/portfolio/trades?page=${page ?? 1}`),
    performance: () => apiFetch<unknown>('/api/portfolio/performance'),
  },
  market: {
    bars: (params: {
      symbol: string
      market: string
      timeframe: string
      limit?: number
    }) => {
      const qs: Record<string, string> = {
        symbol: params.symbol,
        market: params.market,
        timeframe: params.timeframe,
      }
      if (params.limit != null) qs.limit = String(params.limit)
      return apiFetch<Bar[]>(`/api/market-data/bars?${new URLSearchParams(qs)}`)
    },
    latest: (symbol: string, market: string) =>
      apiFetch<unknown>(
        `/api/market-data/latest?symbol=${symbol}&market=${market}`,
      ),
    symbols: () => apiFetch<string[]>('/api/market-data/symbols'),
    status: () =>
      apiFetch<{
        markets: {
          market: string
          symbols: string[]
          total_bars: number
          latest_bar_time: string | null
          staleness_seconds: number | null
          has_gaps: boolean
        }[]
        total_bars: number
        duckdb_size_mb: number
      }>('/api/market-data/status'),
  },
}
