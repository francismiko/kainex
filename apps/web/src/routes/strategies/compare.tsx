import { useState, useMemo } from 'react'
import { createFileRoute } from '@tanstack/react-router'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Badge } from '@/components/ui/badge'
import { Checkbox } from '@/components/ui/checkbox'
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table'
import { LoadingSkeleton } from '@/components/shared/loading-skeleton'
import { EmptyState } from '@/components/shared/empty-state'
import { useStrategies, useRunBacktest } from '@/hooks/use-api'
import { formatPercent, formatNumber } from '@/lib/format'
import { toast } from 'sonner'
import { Loader2, GitCompareArrows } from 'lucide-react'
import type { Strategy, BacktestResult, BacktestMetrics } from '@/types/strategy'
import ReactECharts from 'echarts-for-react'
import type { EChartsOption } from 'echarts'

export const Route = createFileRoute('/strategies/compare')({
  component: StrategyCompare,
})

const STRATEGY_TYPE_LABELS: Record<string, string> = {
  sma_crossover: 'SMA 交叉',
  rsi_mean_reversion: 'RSI 均值回归',
  bollinger_breakout: '布林带突破',
  macd_crossover: 'MACD 交叉',
  momentum: '动量策略',
  dual_ma: '双均线策略',
}

const LINE_COLORS = ['#3b82f6', '#ef4444', '#22c55e', '#f59e0b']

interface CompareEntry {
  strategy: Strategy
  result: BacktestResult
}

function CompareChart({ entries }: { entries: CompareEntry[] }) {
  const option = useMemo<EChartsOption>(() => {
    // Use the longest equity curve's time axis
    let longestTimes: string[] = []
    for (const e of entries) {
      if (e.result.equity_curve.length > longestTimes.length) {
        longestTimes = e.result.equity_curve.map((p) => p.time)
      }
    }

    const series: EChartsOption['series'] = entries.map((entry, i) => ({
      name: entry.strategy.name,
      type: 'line' as const,
      data: entry.result.equity_curve.map((p) => p.value),
      smooth: true,
      showSymbol: false,
      lineStyle: { color: LINE_COLORS[i % LINE_COLORS.length], width: 2 },
    }))

    return {
      backgroundColor: 'transparent',
      legend: {
        show: true,
        top: 0,
        right: 20,
        textStyle: { color: 'var(--color-muted-foreground, #9ca3af)' },
      },
      tooltip: {
        trigger: 'axis',
        backgroundColor: 'rgba(0, 0, 0, 0.85)',
        borderColor: 'rgba(255, 255, 255, 0.08)',
        textStyle: { color: '#d1d5db' },
      },
      xAxis: {
        type: 'category',
        data: longestTimes,
        axisLine: { lineStyle: { color: 'rgba(255, 255, 255, 0.08)' } },
        axisLabel: { color: 'var(--color-muted-foreground, #9ca3af)' },
      },
      yAxis: {
        type: 'value',
        axisLine: { lineStyle: { color: 'rgba(255, 255, 255, 0.08)' } },
        axisLabel: { color: 'var(--color-muted-foreground, #9ca3af)' },
        splitLine: { lineStyle: { color: 'rgba(255, 255, 255, 0.04)' } },
      },
      series,
      grid: { left: 60, right: 20, top: 40, bottom: 30 },
    }
  }, [entries])

  return <ReactECharts option={option} style={{ height: 360 }} />
}

function MetricRow({
  label,
  accessor,
  entries,
  format = 'number',
}: {
  label: string
  accessor: keyof BacktestMetrics
  entries: CompareEntry[]
  format?: 'percent' | 'number' | 'integer'
}) {
  const values = entries.map((e) => e.result.metrics[accessor] as number)

  // Find best value (highest is best, except max_drawdown where lowest abs is best)
  let bestIdx = 0
  if (accessor === 'max_drawdown') {
    values.forEach((v, i) => {
      if (Math.abs(v) < Math.abs(values[bestIdx])) bestIdx = i
    })
  } else {
    values.forEach((v, i) => {
      if (v > values[bestIdx]) bestIdx = i
    })
  }

  function formatVal(v: number) {
    if (format === 'percent') return formatPercent(v)
    if (format === 'integer') return String(Math.round(v))
    return formatNumber(v)
  }

  return (
    <TableRow>
      <TableCell className="font-medium text-muted-foreground">{label}</TableCell>
      {entries.map((entry, i) => (
        <TableCell
          key={entry.strategy.id}
          className={i === bestIdx ? 'font-bold text-primary' : ''}
        >
          {formatVal(values[i])}
        </TableCell>
      ))}
    </TableRow>
  )
}

function StrategyCompare() {
  const { data: strategies, isLoading } = useStrategies()
  const backtestMutation = useRunBacktest()

  const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set())
  const [startDate, setStartDate] = useState('2025-01-01')
  const [endDate, setEndDate] = useState('2026-01-01')
  const [initialCapital, setInitialCapital] = useState('100000')
  const [results, setResults] = useState<CompareEntry[]>([])
  const [running, setRunning] = useState(false)

  function toggleStrategy(id: string) {
    setSelectedIds((prev) => {
      const next = new Set(prev)
      if (next.has(id)) {
        next.delete(id)
      } else if (next.size < 4) {
        next.add(id)
      } else {
        toast.error('最多选择 4 个策略')
      }
      return next
    })
  }

  async function handleCompare() {
    if (selectedIds.size < 2) {
      toast.error('至少选择 2 个策略进行对比')
      return
    }

    const selected = (strategies ?? []).filter((s) => selectedIds.has(s.id))
    setRunning(true)
    setResults([])

    try {
      const entries: CompareEntry[] = []
      for (const strategy of selected) {
        const market = strategy.markets?.[0] ?? strategy.market ?? 'crypto'
        const symbols = strategy.parameters?.symbol
          ? [String(strategy.parameters.symbol)]
          : strategy.symbols?.length
            ? strategy.symbols
            : ['BTC/USDT']

        const result = await backtestMutation.mutateAsync({
          strategy_id: strategy.id,
          start_date: startDate,
          end_date: endDate,
          initial_capital: Number(initialCapital),
          market,
          symbols,
        })

        if (result.equity_curve && result.equity_curve.length > 0) {
          entries.push({ strategy, result })
        }
      }

      if (entries.length < 2) {
        toast.warning('回测完成但有效结果不足 2 个，无法对比。请检查数据。')
      } else {
        setResults(entries)
        toast.success(`${entries.length} 个策略回测完成`)
      }
    } catch (err) {
      toast.error(`回测失败: ${err instanceof Error ? err.message : String(err)}`)
    } finally {
      setRunning(false)
    }
  }

  if (isLoading) return <LoadingSkeleton />

  const allStrategies = strategies ?? []

  return (
    <div className="space-y-6">
      <div className="flex items-center gap-3">
        <GitCompareArrows className="size-6" />
        <h1 className="text-2xl font-bold">策略对比</h1>
      </div>

      {/* Strategy selection + params */}
      <div className="grid gap-4 lg:grid-cols-3">
        <Card className="lg:col-span-2">
          <CardHeader>
            <CardTitle>选择策略 (2-4 个)</CardTitle>
          </CardHeader>
          <CardContent>
            {allStrategies.length === 0 ? (
              <EmptyState title="暂无策略" description="请先创建策略" />
            ) : (
              <div className="grid gap-2 sm:grid-cols-2">
                {allStrategies.map((s) => (
                  <label
                    key={s.id}
                    className="flex items-center gap-3 rounded-md border p-3 cursor-pointer hover:bg-muted/50 transition-colors"
                  >
                    <Checkbox
                      checked={selectedIds.has(s.id)}
                      onCheckedChange={() => toggleStrategy(s.id)}
                    />
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2">
                        <span className="font-medium text-sm truncate">{s.name}</span>
                        {selectedIds.has(s.id) && (
                          <Badge variant="default" className="text-xs">
                            已选
                          </Badge>
                        )}
                      </div>
                      <span className="text-xs text-muted-foreground">
                        {STRATEGY_TYPE_LABELS[s.class_name] ?? s.class_name}
                      </span>
                    </div>
                  </label>
                ))}
              </div>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>回测参数</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="space-y-2">
              <label className="text-sm font-medium">开始日期</label>
              <Input
                type="date"
                value={startDate}
                onChange={(e) => setStartDate(e.target.value)}
              />
            </div>
            <div className="space-y-2">
              <label className="text-sm font-medium">结束日期</label>
              <Input
                type="date"
                value={endDate}
                onChange={(e) => setEndDate(e.target.value)}
              />
            </div>
            <div className="space-y-2">
              <label className="text-sm font-medium">初始资金</label>
              <Input
                type="number"
                value={initialCapital}
                onChange={(e) => setInitialCapital(e.target.value)}
              />
            </div>
            <Button
              className="w-full"
              onClick={handleCompare}
              disabled={running || selectedIds.size < 2}
            >
              {running ? (
                <>
                  <Loader2 className="size-4 animate-spin" />
                  回测中...
                </>
              ) : (
                `开始对比 (${selectedIds.size} 个)`
              )}
            </Button>
          </CardContent>
        </Card>
      </div>

      {/* Results */}
      {running && (
        <div className="flex flex-col items-center justify-center gap-3 py-16">
          <Loader2 className="h-8 w-8 animate-spin text-primary" />
          <span className="text-sm text-muted-foreground">正在回测对比...</span>
        </div>
      )}

      {results.length >= 2 && !running && (
        <>
          {/* Equity curve overlay */}
          <Card>
            <CardHeader>
              <CardTitle>收益曲线对比</CardTitle>
            </CardHeader>
            <CardContent>
              <CompareChart entries={results} />
            </CardContent>
          </Card>

          {/* Metrics comparison table */}
          <Card>
            <CardHeader>
              <CardTitle>关键指标对比</CardTitle>
            </CardHeader>
            <CardContent>
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead className="w-32">指标</TableHead>
                    {results.map((entry, i) => (
                      <TableHead key={entry.strategy.id}>
                        <span
                          className="inline-block w-3 h-3 rounded-full mr-2"
                          style={{ backgroundColor: LINE_COLORS[i % LINE_COLORS.length] }}
                        />
                        {entry.strategy.name}
                      </TableHead>
                    ))}
                  </TableRow>
                </TableHeader>
                <TableBody>
                  <MetricRow label="总收益" accessor="total_return" entries={results} format="percent" />
                  <MetricRow label="年化收益" accessor="annual_return" entries={results} format="percent" />
                  <MetricRow label="夏普比率" accessor="sharpe" entries={results} />
                  <MetricRow label="索提诺比率" accessor="sortino" entries={results} />
                  <MetricRow label="最大回撤" accessor="max_drawdown" entries={results} format="percent" />
                  <MetricRow label="胜率" accessor="win_rate" entries={results} format="percent" />
                  <MetricRow label="盈亏比" accessor="profit_factor" entries={results} />
                  <MetricRow label="交易次数" accessor="trade_count" entries={results} format="integer" />
                </TableBody>
              </Table>
            </CardContent>
          </Card>
        </>
      )}
    </div>
  )
}
