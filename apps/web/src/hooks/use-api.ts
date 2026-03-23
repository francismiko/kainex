import {
  useQuery,
  useMutation,
  useQueryClient,
} from '@tanstack/react-query'
import { api } from '@/lib/api-client'
import type { AlertCreateInput, AlertUpdateInput } from '@/lib/api-client'
import type { StrategyCreateInput, BacktestResult, OptimizeResponse } from '@/types/strategy'

export function useStrategies() {
  return useQuery({
    queryKey: ['strategies'],
    queryFn: api.strategies.list,
  })
}

export function useStrategy(id: string) {
  return useQuery({
    queryKey: ['strategies', id],
    queryFn: () => api.strategies.get(id),
  })
}

export function useCreateStrategy() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (data: StrategyCreateInput) => api.strategies.create(data),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['strategies'] }),
  })
}

export function useDeleteStrategy() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (id: string) => api.strategies.delete(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['strategies'] }),
  })
}

export function useStartStrategy() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (id: string) => api.strategies.start(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['strategies'] }),
  })
}

export function useStopStrategy() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (id: string) => api.strategies.stop(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['strategies'] }),
  })
}

export function usePortfolioSummary() {
  return useQuery({
    queryKey: ['portfolio', 'summary'],
    queryFn: api.portfolio.summary,
  })
}

export function usePositions() {
  return useQuery({
    queryKey: ['portfolio', 'positions'],
    queryFn: api.portfolio.positions,
  })
}

export function useTrades(page?: number) {
  return useQuery({
    queryKey: ['portfolio', 'trades', page],
    queryFn: () => api.portfolio.trades(page),
  })
}

export function useMarketDataStatus() {
  return useQuery({
    queryKey: ['market', 'status'],
    queryFn: api.market.status,
    refetchInterval: 30_000, // refresh every 30s
  })
}

export function useMarketBars(params: {
  symbol: string
  market: string
  timeframe: string
  limit?: number
}) {
  return useQuery({
    queryKey: ['market', 'bars', params],
    queryFn: () => api.market.bars(params),
  })
}

export function useRunBacktest() {
  return useMutation({
    mutationFn: (params: {
      strategy_id: string
      start_date: string
      end_date: string
      initial_capital: number
      market?: string
      symbols?: string[]
    }) => api.backtest.run(params) as Promise<BacktestResult>,
  })
}

export function useBacktestResults() {
  return useQuery({
    queryKey: ['backtest', 'results'],
    queryFn: api.backtest.results,
  })
}

export function useBacktestResult(id: string) {
  return useQuery({
    queryKey: ['backtest', 'results', id],
    queryFn: () => api.backtest.result(id),
    enabled: !!id,
  })
}

export function useOptimize() {
  return useMutation({
    mutationFn: (params: {
      strategy_id: string
      param_grid: Record<string, number[]>
      start_date: string
      end_date: string
      initial_capital: number
      market?: string
      symbols?: string[]
      metric?: string
    }) => api.backtest.optimize(params) as Promise<OptimizeResponse>,
  })
}

// --- Logs ---

export function useLogs(params?: {
  level?: string
  strategy_id?: string
  limit?: number
  offset?: number
}) {
  return useQuery({
    queryKey: ['logs', params],
    queryFn: () => api.logs.list(params),
  })
}

export function useStrategyLogs(strategyId: string, params?: {
  level?: string
  limit?: number
  offset?: number
}) {
  return useQuery({
    queryKey: ['logs', 'strategy', strategyId, params],
    queryFn: () => api.logs.byStrategy(strategyId, params),
    enabled: !!strategyId,
  })
}

// --- Alerts ---

export function useAlerts() {
  return useQuery({
    queryKey: ['alerts'],
    queryFn: api.alerts.list,
  })
}

export function useCreateAlert() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (data: AlertCreateInput) => api.alerts.create(data),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['alerts'] }),
  })
}

export function useDeleteAlert() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (id: string) => api.alerts.delete(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['alerts'] }),
  })
}

export function useUpdateAlert() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ id, data }: { id: string; data: AlertUpdateInput }) =>
      api.alerts.update(id, data),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['alerts'] }),
  })
}
