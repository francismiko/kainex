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
import { LoadingSkeleton } from '@/components/shared/loading-skeleton'
import { EmptyState } from '@/components/shared/empty-state'
import {
  useStrategy,
  useStartStrategy,
  useStopStrategy,
  useDeleteStrategy,
  useRunBacktest,
  useBacktestResults,
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
import { toast } from 'sonner'
import { AlertTriangle, ChevronDown, ChevronRight, History, Loader2, Play, Square, Trash2 } from 'lucide-react'
import { formatPercent, formatNumber, formatDateTime } from '@/lib/format'
import type { BacktestResult } from '@/types/strategy'

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

function StrategyDetail() {
  const { id } = Route.useParams()
  const navigate = useNavigate()
  const { data: strategy, isLoading, isError } = useStrategy(id)
  const startMutation = useStartStrategy()
  const stopMutation = useStopStrategy()
  const deleteMutation = useDeleteStrategy()
  const backtestMutation = useRunBacktest()
  const { data: allBacktestResults } = useBacktestResults()

  const [backtestResult, setBacktestResult] = useState<BacktestResult | null>(null)
  const [backtestDialogOpen, setBacktestDialogOpen] = useState(false)
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false)
  const [startDate, setStartDate] = useState('2025-01-01')
  const [endDate, setEndDate] = useState('2026-01-01')
  const [initialCapital, setInitialCapital] = useState('100000')
  const [backtestEmpty, setBacktestEmpty] = useState(false)
  const [expandedHistoryId, setExpandedHistoryId] = useState<string | null>(null)

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
