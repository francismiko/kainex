import { useState } from 'react'
import { createFileRoute, Link } from '@tanstack/react-router'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
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
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { LoadingSkeleton } from '@/components/shared/loading-skeleton'
import { EmptyState } from '@/components/shared/empty-state'
import { useStrategies, useCreateStrategy } from '@/hooks/use-api'
import { formatPercent } from '@/lib/format'
import { toast } from 'sonner'
import { Plus } from 'lucide-react'
import type { Strategy } from '@/types/strategy'

export const Route = createFileRoute('/strategies/')({
  component: StrategiesList,
})

const STRATEGY_TYPES = [
  { value: 'sma_crossover', label: 'SMA 交叉' },
  { value: 'rsi_mean_reversion', label: 'RSI 均值回归' },
  { value: 'bollinger_breakout', label: '布林带突破' },
  { value: 'macd_crossover', label: 'MACD 交叉' },
  { value: 'momentum', label: '动量策略' },
  { value: 'dual_ma', label: '双均线策略' },
] as const

const MARKETS = [
  { value: 'a_stock', label: 'A股' },
  { value: 'crypto', label: '加密货币' },
  { value: 'us_stock', label: '美股' },
] as const

function apiToDisplay(s: Strategy) {
  return {
    id: s.id,
    name: s.name,
    market: s.market || (s.markets?.[0] ?? ''),
    status: s.status,
    pnl: s.pnl,
  }
}

function CreateStrategyDialog() {
  const createMutation = useCreateStrategy()
  const [open, setOpen] = useState(false)
  const [name, setName] = useState('')
  const [classname, setClassname] = useState('')
  const [market, setMarket] = useState('')
  const [symbol, setSymbol] = useState('')

  function resetForm() {
    setName('')
    setClassname('')
    setMarket('')
    setSymbol('')
  }

  function handleSubmit() {
    if (!name.trim() || !classname || !market) {
      toast.error('请填写所有必填字段')
      return
    }

    createMutation.mutate(
      {
        name: name.trim(),
        class_name: classname,
        markets: [market],
        timeframes: ['1d'],
        parameters: symbol.trim() ? { symbol: symbol.trim() } : {},
      },
      {
        onSuccess: () => {
          toast.success('策略创建成功')
          setOpen(false)
          resetForm()
        },
        onError: (err) => {
          toast.error(`创建失败: ${err.message}`)
        },
      },
    )
  }

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger asChild>
        <Button size="sm">
          <Plus className="size-4" />
          新建策略
        </Button>
      </DialogTrigger>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>新建策略</DialogTitle>
          <DialogDescription>创建一个新的量化交易策略</DialogDescription>
        </DialogHeader>
        <div className="space-y-4 py-2">
          <div className="space-y-2">
            <label className="text-sm font-medium">策略名称</label>
            <Input
              placeholder="输入策略名称"
              value={name}
              onChange={(e) => setName(e.target.value)}
            />
          </div>
          <div className="space-y-2">
            <label className="text-sm font-medium">策略类型</label>
            <Select value={classname} onValueChange={setClassname}>
              <SelectTrigger className="w-full">
                <SelectValue placeholder="选择策略类型" />
              </SelectTrigger>
              <SelectContent>
                {STRATEGY_TYPES.map((t) => (
                  <SelectItem key={t.value} value={t.value}>
                    {t.label}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
          <div className="space-y-2">
            <label className="text-sm font-medium">市场</label>
            <Select value={market} onValueChange={setMarket}>
              <SelectTrigger className="w-full">
                <SelectValue placeholder="选择市场" />
              </SelectTrigger>
              <SelectContent>
                {MARKETS.map((m) => (
                  <SelectItem key={m.value} value={m.value}>
                    {m.label}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
          <div className="space-y-2">
            <label className="text-sm font-medium">标的</label>
            <Input
              placeholder="如 BTC/USDT, 000001.SZ"
              value={symbol}
              onChange={(e) => setSymbol(e.target.value)}
            />
          </div>
        </div>
        <DialogFooter>
          <Button
            variant="outline"
            onClick={() => setOpen(false)}
            disabled={createMutation.isPending}
          >
            取消
          </Button>
          <Button
            onClick={handleSubmit}
            disabled={createMutation.isPending}
          >
            {createMutation.isPending ? '创建中...' : '创建'}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}

function StrategiesList() {
  const { data, isLoading, isError } = useStrategies()

  if (isLoading) return <LoadingSkeleton />

  const strategies = data ? data.map(apiToDisplay) : []

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold">策略管理</h1>
        <div className="flex items-center gap-2">
          {isError && (
            <Badge variant="outline" className="text-muted-foreground">
              无法连接后端
            </Badge>
          )}
          <CreateStrategyDialog />
        </div>
      </div>

      {strategies.length === 0 ? (
        <EmptyState
          title="暂无策略"
          description="点击上方「新建策略」创建你的第一个量化策略"
        />
      ) : (
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
          {strategies.map((s) => (
            <Link key={s.id} to="/strategies/$id" params={{ id: s.id }}>
              <Card className="cursor-pointer transition-colors hover:border-primary/50">
                <CardHeader className="flex flex-row items-center justify-between pb-2">
                  <CardTitle className="text-base">{s.name}</CardTitle>
                  <Badge
                    variant={
                      s.status === 'running'
                        ? 'default'
                        : 'outline'
                    }
                  >
                    {s.status === 'running' ? '运行中' : s.status === 'error' ? '异常' : '已停止'}
                  </Badge>
                </CardHeader>
                <CardContent>
                  <div className="flex items-center justify-between text-sm text-muted-foreground">
                    <span>{MARKETS.find((m) => m.value === s.market)?.label ?? s.market}</span>
                    <span
                      className={
                        s.pnl > 0
                          ? 'font-medium text-green-500'
                          : s.pnl < 0
                            ? 'font-medium text-red-500'
                            : ''
                      }
                    >
                      {s.pnl > 0 ? '+' : ''}{formatPercent(s.pnl)}
                    </span>
                  </div>
                </CardContent>
              </Card>
            </Link>
          ))}
        </div>
      )}
    </div>
  )
}
