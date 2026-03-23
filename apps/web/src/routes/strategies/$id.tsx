import { useState } from 'react'
import { createFileRoute } from '@tanstack/react-router'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { LoadingSkeleton } from '@/components/shared/loading-skeleton'
import { useStrategy, useStartStrategy, useStopStrategy, useRunBacktest } from '@/hooks/use-api'
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
import type { BacktestResult } from '@/types/strategy'

export const Route = createFileRoute('/strategies/$id')({
  component: StrategyDetail,
})

function StrategyDetail() {
  const { id } = Route.useParams()
  const { data: strategy, isLoading, isError } = useStrategy(id)
  const startMutation = useStartStrategy()
  const stopMutation = useStopStrategy()
  const backtestMutation = useRunBacktest()

  const [backtestResult, setBacktestResult] = useState<BacktestResult | null>(null)
  const [dialogOpen, setDialogOpen] = useState(false)
  const [startDate, setStartDate] = useState('2025-01-01')
  const [endDate, setEndDate] = useState('2026-01-01')
  const [initialCapital, setInitialCapital] = useState('100000')

  function handleRunBacktest() {
    backtestMutation.mutate(
      {
        strategy_id: id,
        start_date: startDate,
        end_date: endDate,
        initial_capital: Number(initialCapital),
      },
      {
        onSuccess: (data) => {
          setBacktestResult(data)
          setDialogOpen(false)
        },
      },
    )
  }

  if (isLoading) return <LoadingSkeleton />

  return (
    <div className="space-y-6">
      <div className="flex items-center gap-3">
        <h1 className="text-2xl font-bold">策略详情</h1>
        <Badge>ID: {id}</Badge>
        {isError && (
          <Badge variant="outline" className="text-muted-foreground">
            无法连接后端
          </Badge>
        )}
      </div>

      {strategy && (
        <div className="flex items-center gap-3">
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
          {strategy.status === 'stopped' && (
            <Button
              size="sm"
              onClick={() => startMutation.mutate(id)}
              disabled={startMutation.isPending}
            >
              启动
            </Button>
          )}
          {strategy.status === 'running' && (
            <Button
              size="sm"
              variant="outline"
              onClick={() => stopMutation.mutate(id)}
              disabled={stopMutation.isPending}
            >
              停止
            </Button>
          )}
        </div>
      )}

      <div className="grid gap-4 md:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle>策略参数</CardTitle>
          </CardHeader>
          <CardContent>
            {strategy ? (
              <dl className="space-y-2 text-sm">
                <div className="flex justify-between">
                  <dt className="text-muted-foreground">名称</dt>
                  <dd>{strategy.name}</dd>
                </div>
                <div className="flex justify-between">
                  <dt className="text-muted-foreground">市场</dt>
                  <dd>{strategy.market}</dd>
                </div>
                <div className="flex justify-between">
                  <dt className="text-muted-foreground">标的</dt>
                  <dd>{strategy.symbols.join(', ')}</dd>
                </div>
                <div className="flex justify-between">
                  <dt className="text-muted-foreground">描述</dt>
                  <dd>{strategy.description || '-'}</dd>
                </div>
              </dl>
            ) : (
              <p className="text-sm text-muted-foreground">策略参数配置将在此展示</p>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>实时信号</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-sm text-muted-foreground">策略生成的实时交易信号将在此展示</p>
          </CardContent>
        </Card>
      </div>

      <Card>
        <CardHeader className="flex flex-row items-center justify-between">
          <CardTitle>回测结果</CardTitle>
          <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
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
                  <label className="text-sm text-muted-foreground">开始日期</label>
                  <Input
                    type="date"
                    value={startDate}
                    onChange={(e) => setStartDate(e.target.value)}
                  />
                </div>
                <div className="space-y-2">
                  <label className="text-sm text-muted-foreground">结束日期</label>
                  <Input
                    type="date"
                    value={endDate}
                    onChange={(e) => setEndDate(e.target.value)}
                  />
                </div>
                <div className="space-y-2">
                  <label className="text-sm text-muted-foreground">初始资金</label>
                  <Input
                    type="number"
                    value={initialCapital}
                    onChange={(e) => setInitialCapital(e.target.value)}
                  />
                </div>
              </div>
              <DialogFooter>
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
            <div className="flex items-center justify-center py-12">
              <div className="animate-spin h-8 w-8 rounded-full border-2 border-primary border-t-transparent" />
              <span className="ml-3 text-sm text-muted-foreground">回测运行中...</span>
            </div>
          )}
          {backtestResult && !backtestMutation.isPending && (
            <BacktestPanel result={backtestResult} />
          )}
          {!backtestResult && !backtestMutation.isPending && (
            <p className="text-sm text-muted-foreground">点击"运行回测"设置参数后查看结果</p>
          )}
        </CardContent>
      </Card>
    </div>
  )
}
