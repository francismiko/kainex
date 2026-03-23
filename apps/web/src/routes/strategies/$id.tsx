import { useState } from 'react'
import { createFileRoute, useNavigate } from '@tanstack/react-router'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { LoadingSkeleton } from '@/components/shared/loading-skeleton'
import { EmptyState } from '@/components/shared/empty-state'
import {
  useStrategy,
  useStartStrategy,
  useStopStrategy,
  useDeleteStrategy,
  useRunBacktest,
  useBacktestResults,
  useOptimize,
} from '@/hooks/use-api'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from '@/components/ui/dialog'
import { BacktestPanel } from '@/components/strategy/backtest-panel'
import { OptimizeResultPanel } from '@/components/strategy/optimize-result-panel'
import { toast } from 'sonner'
import { AlertTriangle, ChevronDown, ChevronRight, History, Loader2, Play, Settings2, Square, Trash2 } from 'lucide-react'
import { formatPercent, formatNumber, formatDateTime } from '@/lib/format'
import type { BacktestResult, OptimizeResponse } from '@/types/strategy'

export const Route = createFileRoute('/strategies/$id')({
  component: StrategyDetail,
})

const STRATEGY_TYPE_LABELS: Record<string, string> = {
  sma_crossover: 'SMA 交叉',
  rsi_mean_reversion: 'RSI 均值回归',
  bollinger_breakout: '布林带突破',
  macd_crossover: 'MACD 交叉',
  momentum: '动量策略',
  dual_ma: '双均线策略',
}

const MARKET_LABELS: Record<string, string> = {
  a_stock: 'A股',
  crypto: '加密货币',
  us_stock: '美股',
}

/** Known tunable parameters per strategy type (excludes non-numeric like ma_type). */
const STRATEGY_PARAM_DEFS: Record<string, { key: string; label: string; defaultRange: string }[]> = {
  sma_crossover: [
    { key: 'short_window', label: '短期窗口', defaultRange: '5,10,15,20' },
    { key: 'long_window', label: '长期窗口', defaultRange: '20,30,40,50,60' },
  ],
  rsi_mean_reversion: [
    { key: 'rsi_period', label: 'RSI 周期', defaultRange: '7,10,14,21' },
    { key: 'oversold', label: '超卖阈值', defaultRange: '20,25,30,35' },
    { key: 'overbought', label: '超买阈值', defaultRange: '65,70,75,80' },
  ],
  bollinger_breakout: [
    { key: 'bb_period', label: '布林带周期', defaultRange: '10,15,20,25,30' },
    { key: 'bb_std', label: '标准差倍数', defaultRange: '1.5,2,2.5,3' },
  ],
  macd_crossover: [
    { key: 'fast_period', label: '快线周期', defaultRange: '8,10,12,15' },
    { key: 'slow_period', label: '慢线周期', defaultRange: '20,24,26,30' },
    { key: 'signal_period', label: '信号线周期', defaultRange: '7,9,11' },
  ],
  momentum: [
    { key: 'lookback', label: '回望周期', defaultRange: '10,15,20,25,30' },
    { key: 'threshold', label: '阈值', defaultRange: '0.01,0.02,0.03,0.05' },
  ],
  dual_ma: [
    { key: 'fast_period', label: '快线周期', defaultRange: '5,10,15,20' },
    { key: 'slow_period', label: '慢线周期', defaultRange: '20,30,40,50,60' },
  ],
}

const OPTIMIZE_METRICS = [
  { value: 'sharpe_ratio', label: '夏普比率' },
  { value: 'total_return', label: '总收益' },
  { value: 'win_rate', label: '胜率' },
  { value: 'max_drawdown', label: '最大回撤' },
]

function StrategyDetail() {
  const { id } = Route.useParams()
  const navigate = useNavigate()
  const { data: strategy, isLoading, isError } = useStrategy(id)
  const startMutation = useStartStrategy()
  const stopMutation = useStopStrategy()
  const deleteMutation = useDeleteStrategy()
  const backtestMutation = useRunBacktest()
  const optimizeMutation = useOptimize()
  const { data: allBacktestResults } = useBacktestResults()

  const [backtestResult, setBacktestResult] = useState<BacktestResult | null>(null)
  const [backtestDialogOpen, setBacktestDialogOpen] = useState(false)
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false)
  const [startDate, setStartDate] = useState('2025-01-01')
  const [endDate, setEndDate] = useState('2026-01-01')
  const [initialCapital, setInitialCapital] = useState('100000')
  const [backtestEmpty, setBacktestEmpty] = useState(false)
  const [expandedHistoryId, setExpandedHistoryId] = useState<string | null>(null)

  // Optimize state
  const [optimizeDialogOpen, setOptimizeDialogOpen] = useState(false)
  const [optimizeResult, setOptimizeResult] = useState<OptimizeResponse | null>(null)
  const [optimizeMetric, setOptimizeMetric] = useState('sharpe_ratio')
  const [optimizeStartDate, setOptimizeStartDate] = useState('2025-01-01')
  const [optimizeEndDate, setOptimizeEndDate] = useState('2026-01-01')
  const [optimizeCapital, setOptimizeCapital] = useState('100000')

  // Parameter grid state: key => comma-separated values string
  const paramDefs = strategy ? STRATEGY_PARAM_DEFS[strategy.class_name] ?? [] : []
  const [paramGridValues, setParamGridValues] = useState<Record<string, string>>(() => {
    const initial: Record<string, string> = {}
    // Will be populated when dialog opens
    return initial
  })

  // Filter backtest history for current strategy
  const backtestHistory = (allBacktestResults ?? []).filter(
    (r) => r.strategy_id === id,
  )

  function handleRunBacktest() {
    setBacktestEmpty(false)
    const market = strategy?.markets?.[0] ?? strategy?.market ?? 'crypto'
    const symbols = strategy?.parameters?.symbol
      ? [String(strategy.parameters.symbol)]
      : strategy?.symbols?.length
        ? strategy.symbols
        : ['BTC/USDT']

    backtestMutation.mutate(
      {
        strategy_id: id,
        start_date: startDate,
        end_date: endDate,
        initial_capital: Number(initialCapital),
        market,
        symbols,
      },
      {
        onSuccess: (data) => {
          if (!data.equity_curve || data.equity_curve.length === 0) {
            setBacktestEmpty(true)
            setBacktestResult(null)
            toast.warning('回测完成，但无可用数据。请先运行 just seed 导入样本数据。')
          } else {
            setBacktestResult(data)
            setBacktestEmpty(false)
            toast.success('回测完成')
          }
          setBacktestDialogOpen(false)
        },
        onError: (err) => {
          toast.error(`回测失败: ${err.message}`)
        },
      },
    )
  }

  function handleOpenOptimize() {
    // Initialize param grid values from defaults when opening dialog
    const initial: Record<string, string> = {}
    for (const def of paramDefs) {
      initial[def.key] = paramGridValues[def.key] ?? def.defaultRange
    }
    setParamGridValues(initial)
    setOptimizeDialogOpen(true)
  }

  function handleRunOptimize() {
    const market = strategy?.markets?.[0] ?? strategy?.market ?? 'crypto'
    const symbols = strategy?.parameters?.symbol
      ? [String(strategy.parameters.symbol)]
      : strategy?.symbols?.length
        ? strategy.symbols
        : ['BTC/USDT']

    // Parse param grid: convert comma-separated strings to number arrays
    const paramGrid: Record<string, number[]> = {}
    let totalCombinations = 1
    for (const def of paramDefs) {
      const raw = paramGridValues[def.key] ?? def.defaultRange
      const values = raw
        .split(',')
        .map((s) => s.trim())
        .filter((s) => s !== '')
        .map(Number)
        .filter((n) => !isNaN(n))
      if (values.length === 0) {
        toast.error(`参数「${def.label}」至少需要一个有效数值`)
        return
      }
      paramGrid[def.key] = values
      totalCombinations *= values.length
    }

    if (Object.keys(paramGrid).length === 0) {
      toast.error('没有可优化的参数')
      return
    }

    optimizeMutation.mutate(
      {
        strategy_id: id,
        param_grid: paramGrid,
        start_date: optimizeStartDate,
        end_date: optimizeEndDate,
        initial_capital: Number(optimizeCapital),
        market,
        symbols,
        metric: optimizeMetric,
      },
      {
        onSuccess: (data) => {
          setOptimizeResult(data)
          setOptimizeDialogOpen(false)
          toast.success(`优化完成，共测试 ${data.total_combinations} 个组合`)
        },
        onError: (err) => {
          toast.error(`优化失败: ${err.message}`)
        },
      },
    )
  }

  function handleStart() {
    startMutation.mutate(id, {
      onSuccess: () => toast.success('策略已启动'),
      onError: (err) => toast.error(`启动失败: ${err.message}`),
    })
  }

  function handleStop() {
    stopMutation.mutate(id, {
      onSuccess: () => toast.success('策略已停止'),
      onError: (err) => toast.error(`停止失败: ${err.message}`),
    })
  }

  function handleDelete() {
    deleteMutation.mutate(id, {
      onSuccess: () => {
        toast.success('策略已删除')
        navigate({ to: '/strategies' })
      },
      onError: (err) => toast.error(`删除失败: ${err.message}`),
    })
  }

  if (isLoading) return <LoadingSkeleton />

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <h1 className="text-2xl font-bold">
            {strategy?.name ?? '策略详情'}
          </h1>
          {strategy && (
            <Badge
              variant={
                strategy.status === 'running'
                  ? 'default'
                  : strategy.status === 'error'
                    ? 'destructive'
                    : 'outline'
              }
            >
              {strategy.status === 'running' ? '运行中' : strategy.status === 'error' ? '异常' : '已停止'}
            </Badge>
          )}
          {isError && (
            <Badge variant="outline" className="text-muted-foreground">
              无法连接后端
            </Badge>
          )}
        </div>

        {/* Action buttons */}
        {strategy && (
          <div className="flex items-center gap-2">
            {strategy.status !== 'running' && (
              <Button
                size="sm"
                onClick={handleStart}
                disabled={startMutation.isPending}
              >
                <Play className="size-4" />
                {startMutation.isPending ? '启动中...' : '启动'}
              </Button>
            )}
            {strategy.status === 'running' && (
              <Button
                size="sm"
                variant="outline"
                onClick={handleStop}
                disabled={stopMutation.isPending}
              >
                <Square className="size-4" />
                {stopMutation.isPending ? '停止中...' : '停止'}
              </Button>
            )}
            <Dialog open={deleteDialogOpen} onOpenChange={setDeleteDialogOpen}>
              <DialogTrigger asChild>
                <Button size="sm" variant="destructive">
                  <Trash2 className="size-4" />
                  删除
                </Button>
              </DialogTrigger>
              <DialogContent>
                <DialogHeader>
                  <DialogTitle>确认删除</DialogTitle>
                  <DialogDescription>
                    确定要删除策略「{strategy.name}」吗？此操作不可撤销。
                  </DialogDescription>
                </DialogHeader>
                <DialogFooter>
                  <Button variant="outline" onClick={() => setDeleteDialogOpen(false)}>
                    取消
                  </Button>
                  <Button
                    variant="destructive"
                    onClick={handleDelete}
                    disabled={deleteMutation.isPending}
                  >
                    {deleteMutation.isPending ? '删除中...' : '确认删除'}
                  </Button>
                </DialogFooter>
              </DialogContent>
            </Dialog>
          </div>
        )}
      </div>

      {/* Strategy info cards */}
      <div className="grid gap-4 md:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle>基本信息</CardTitle>
          </CardHeader>
          <CardContent>
            {strategy ? (
              <dl className="space-y-2 text-sm">
                <div className="flex justify-between">
                  <dt className="text-muted-foreground">名称</dt>
                  <dd>{strategy.name}</dd>
                </div>
                <div className="flex justify-between">
                  <dt className="text-muted-foreground">策略类型</dt>
                  <dd>{STRATEGY_TYPE_LABELS[strategy.class_name] ?? strategy.class_name}</dd>
                </div>
                <div className="flex justify-between">
                  <dt className="text-muted-foreground">市场</dt>
                  <dd>
                    {strategy.markets?.map((m) => MARKET_LABELS[m] ?? m).join(', ') || '-'}
                  </dd>
                </div>
                <div className="flex justify-between">
                  <dt className="text-muted-foreground">时间周期</dt>
                  <dd>{strategy.timeframes?.join(', ') || '-'}</dd>
                </div>
                <div className="flex justify-between">
                  <dt className="text-muted-foreground">标的</dt>
                  <dd>{strategy.parameters?.symbol ? String(strategy.parameters.symbol) : strategy.symbols?.join(', ') || '-'}</dd>
                </div>
                <div className="flex justify-between">
                  <dt className="text-muted-foreground">描述</dt>
                  <dd>{strategy.description || '-'}</dd>
                </div>
              </dl>
            ) : (
              <p className="text-sm text-muted-foreground">策略信息将在此展示</p>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>策略参数</CardTitle>
          </CardHeader>
          <CardContent>
            {strategy?.parameters && Object.keys(strategy.parameters).length > 0 ? (
              <dl className="space-y-2 text-sm">
                {Object.entries(strategy.parameters).map(([key, value]) => (
                  <div key={key} className="flex justify-between">
                    <dt className="text-muted-foreground font-mono">{key}</dt>
                    <dd className="font-mono">{String(value)}</dd>
                  </div>
                ))}
              </dl>
            ) : (
              <p className="text-sm text-muted-foreground">使用默认参数</p>
            )}
          </CardContent>
        </Card>
      </div>

      {/* Backtest section */}
      <Card>
        <CardHeader className="flex flex-row items-center justify-between">
          <CardTitle>回测结果</CardTitle>
          <div className="flex items-center gap-2">
            <Button
              size="sm"
              variant="outline"
              onClick={handleOpenOptimize}
              disabled={paramDefs.length === 0}
            >
              <Settings2 className="size-4" />
              参数优化
            </Button>
            <Dialog open={backtestDialogOpen} onOpenChange={setBacktestDialogOpen}>
              <DialogTrigger asChild>
                <Button size="sm">运行回测</Button>
              </DialogTrigger>
              <DialogContent>
                <DialogHeader>
                  <DialogTitle>回测参数</DialogTitle>
                  <DialogDescription>设置回测时间范围和初始资金</DialogDescription>
                </DialogHeader>
                <div className="space-y-4 py-2">
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
                </div>
                <DialogFooter>
                  <Button
                    variant="outline"
                    onClick={() => setBacktestDialogOpen(false)}
                    disabled={backtestMutation.isPending}
                  >
                    取消
                  </Button>
                  <Button
                    onClick={handleRunBacktest}
                    disabled={backtestMutation.isPending}
                  >
                    {backtestMutation.isPending ? '回测中...' : '开始回测'}
                  </Button>
                </DialogFooter>
              </DialogContent>
            </Dialog>
          </div>
        </CardHeader>
        <CardContent>
          {backtestMutation.isPending && (
            <div className="flex flex-col items-center justify-center gap-3 py-16">
              <Loader2 className="h-8 w-8 animate-spin text-primary" />
              <span className="text-sm text-muted-foreground">正在回测...</span>
            </div>
          )}
          {backtestEmpty && !backtestMutation.isPending && (
            <EmptyState
              icon={AlertTriangle}
              title="无可用数据"
              description="回测期间没有历史数据。请先运行 just seed 导入样本数据，然后重试。"
            />
          )}
          {backtestResult && !backtestMutation.isPending && (
            <BacktestPanel result={backtestResult} />
          )}
          {!backtestResult && !backtestEmpty && !backtestMutation.isPending && (
            <p className="text-center text-sm text-muted-foreground py-8">
              点击「运行回测」设置参数后查看结果
            </p>
          )}
        </CardContent>
      </Card>

      {/* Optimize dialog */}
      <Dialog open={optimizeDialogOpen} onOpenChange={setOptimizeDialogOpen}>
        <DialogContent className="max-w-lg">
          <DialogHeader>
            <DialogTitle>参数优化</DialogTitle>
            <DialogDescription>
              设置参数范围进行网格搜索，找到最优参数组合
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-4 py-2 max-h-[60vh] overflow-y-auto">
            {paramDefs.length > 0 && (
              <div className="space-y-3">
                <p className="text-sm font-medium">参数范围（逗号分隔）</p>
                {paramDefs.map((def) => (
                  <div key={def.key} className="space-y-1">
                    <label className="text-sm text-muted-foreground">{def.label} ({def.key})</label>
                    <Input
                      placeholder={def.defaultRange}
                      value={paramGridValues[def.key] ?? def.defaultRange}
                      onChange={(e) =>
                        setParamGridValues((prev) => ({ ...prev, [def.key]: e.target.value }))
                      }
                    />
                  </div>
                ))}
              </div>
            )}
            <div className="grid grid-cols-2 gap-3">
              <div className="space-y-1">
                <label className="text-sm font-medium">开始日期</label>
                <Input
                  type="date"
                  value={optimizeStartDate}
                  onChange={(e) => setOptimizeStartDate(e.target.value)}
                />
              </div>
              <div className="space-y-1">
                <label className="text-sm font-medium">结束日期</label>
                <Input
                  type="date"
                  value={optimizeEndDate}
                  onChange={(e) => setOptimizeEndDate(e.target.value)}
                />
              </div>
            </div>
            <div className="space-y-1">
              <label className="text-sm font-medium">初始资金</label>
              <Input
                type="number"
                value={optimizeCapital}
                onChange={(e) => setOptimizeCapital(e.target.value)}
              />
            </div>
            <div className="space-y-1">
              <label className="text-sm font-medium">优化目标指标</label>
              <Select value={optimizeMetric} onValueChange={setOptimizeMetric}>
                <SelectTrigger className="w-full">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {OPTIMIZE_METRICS.map((m) => (
                    <SelectItem key={m.value} value={m.value}>
                      {m.label}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
          </div>
          <DialogFooter>
            <Button
              variant="outline"
              onClick={() => setOptimizeDialogOpen(false)}
              disabled={optimizeMutation.isPending}
            >
              取消
            </Button>
            <Button
              onClick={handleRunOptimize}
              disabled={optimizeMutation.isPending}
            >
              {optimizeMutation.isPending
                ? `正在优化 ${(() => {
                    let n = 1
                    for (const def of paramDefs) {
                      const raw = paramGridValues[def.key] ?? def.defaultRange
                      n *= raw.split(',').filter((s) => s.trim() !== '').length
                    }
                    return n
                  })()} 个组合...`
                : '开始优化'}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Optimize loading state */}
      {optimizeMutation.isPending && (
        <Card>
          <CardContent className="py-16">
            <div className="flex flex-col items-center justify-center gap-3">
              <Loader2 className="h-8 w-8 animate-spin text-primary" />
              <span className="text-sm text-muted-foreground">
                正在优化 {(() => {
                  let n = 1
                  for (const def of paramDefs) {
                    const raw = paramGridValues[def.key] ?? def.defaultRange
                    n *= raw.split(',').filter((s) => s.trim() !== '').length
                  }
                  return n
                })()} 个组合...
              </span>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Optimize results */}
      {optimizeResult && !optimizeMutation.isPending && (
        <OptimizeResultPanel data={optimizeResult} metric={optimizeMetric} />
      )}

      {/* Backtest history */}
      <Card>
        <CardHeader className="flex flex-row items-center gap-2">
          <History className="size-5 text-muted-foreground" />
          <CardTitle>历史回测记录</CardTitle>
        </CardHeader>
        <CardContent>
          {backtestHistory.length === 0 ? (
            <p className="text-center text-sm text-muted-foreground py-8">
              暂无历史回测记录
            </p>
          ) : (
            <div className="overflow-x-auto">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead className="w-8" />
                  <TableHead>时间</TableHead>
                  <TableHead>状态</TableHead>
                  <TableHead className="text-right">夏普比率</TableHead>
                  <TableHead className="text-right">总收益</TableHead>
                  <TableHead className="text-right">最大回撤</TableHead>
                  <TableHead className="text-right">胜率</TableHead>
                  <TableHead className="text-right">交易次数</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {backtestHistory.map((record) => {
                  const rid = record.id ?? record.strategy_id ?? ''
                  const isExpanded = expandedHistoryId === rid
                  return (
                    <HistoryRow
                      key={rid}
                      record={record}
                      isExpanded={isExpanded}
                      onToggle={() =>
                        setExpandedHistoryId(isExpanded ? null : rid)
                      }
                    />
                  )
                })}
              </TableBody>
            </Table>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  )
}

function HistoryRow({
  record,
  isExpanded,
  onToggle,
}: {
  record: BacktestResult
  isExpanded: boolean
  onToggle: () => void
}) {
  const { metrics } = record
  const hasEquity = record.equity_curve && record.equity_curve.length > 0
  const firstTime = hasEquity ? record.equity_curve[0].time : '-'

  return (
    <>
      <TableRow
        className="cursor-pointer hover:bg-muted/50"
        onClick={onToggle}
      >
        <TableCell>
          {isExpanded ? (
            <ChevronDown className="size-4 text-muted-foreground" />
          ) : (
            <ChevronRight className="size-4 text-muted-foreground" />
          )}
        </TableCell>
        <TableCell className="text-muted-foreground">
          {firstTime !== '-' ? formatDateTime(firstTime) : '-'}
        </TableCell>
        <TableCell>
          <Badge variant={record.status === 'completed' ? 'default' : 'outline'}>
            {record.status ?? '完成'}
          </Badge>
        </TableCell>
        <TableCell className="text-right font-mono">
          {formatNumber(metrics.sharpe)}
        </TableCell>
        <TableCell
          className="text-right font-mono"
          style={{
            color: metrics.total_return >= 0
              ? 'var(--color-profit)'
              : 'var(--color-loss)',
          }}
        >
          {formatPercent(metrics.total_return)}
        </TableCell>
        <TableCell
          className="text-right font-mono"
          style={{ color: 'var(--color-loss)' }}
        >
          {formatPercent(metrics.max_drawdown)}
        </TableCell>
        <TableCell className="text-right font-mono">
          {formatPercent(metrics.win_rate)}
        </TableCell>
        <TableCell className="text-right font-mono">
          {metrics.trade_count}
        </TableCell>
      </TableRow>
      {isExpanded && hasEquity && (
        <TableRow>
          <TableCell colSpan={8} className="p-0">
            <div className="p-4 bg-muted/20">
              <BacktestPanel result={record} />
            </div>
          </TableCell>
        </TableRow>
      )}
    </>
  )
}
