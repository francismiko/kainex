import type { Strategy } from '@/types/strategy'
import type { Portfolio, Position, Trade } from '@/types/portfolio'
import type { Bar } from '@/types/market'

const API_BASE = 'http://localhost:8000'

export async function apiFetch<T>(
  path: string,
  options?: RequestInit,
): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    headers: { 'Content-Type': 'application/json', ...options?.headers },
    ...options,
  })
  if (!res.ok) {
    throw new Error(`API error: ${res.status} ${res.statusText}`)
  }
  return res.json() as Promise<T>
}

export const api = {
  strategies: {
    list: () => apiFetch<Strategy[]>('/api/strategies'),
    get: (id: string) => apiFetch<Strategy>(`/api/strategies/${id}`),
    create: (data: unknown) =>
      apiFetch<Strategy>('/api/strategies', {
        method: 'POST',
        body: JSON.stringify(data),
      }),
    start: (id: string) =>
      apiFetch<void>(`/api/strategies/${id}/start`, { method: 'POST' }),
    stop: (id: string) =>
      apiFetch<void>(`/api/strategies/${id}/stop`, { method: 'POST' }),
  },
  backtest: {
    run: (data: unknown) =>
      apiFetch<unknown>('/api/backtest/run', {
        method: 'POST',
        body: JSON.stringify(data),
      }),
    results: () => apiFetch<unknown[]>('/api/backtest/results'),
    result: (id: string) => apiFetch<unknown>(`/api/backtest/results/${id}`),
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
  },
}
