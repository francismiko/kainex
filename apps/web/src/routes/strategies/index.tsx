import { createFileRoute, Link } from '@tanstack/react-router'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { LoadingSkeleton } from '@/components/shared/loading-skeleton'
import { useStrategies } from '@/hooks/use-api'
import { formatPercent } from '@/lib/format'
import type { Strategy } from '@/types/strategy'

export const Route = createFileRoute('/strategies/')({
  component: StrategiesList,
})

const mockStrategies = [
  { id: '1', name: 'SMA 交叉', market: 'A股', timeframe: '1d', status: 'running' as const, pnl: 5.2 },
  { id: '2', name: 'RSI 均值回归', market: '加密货币', timeframe: '1h', status: 'running' as const, pnl: 12.8 },
  { id: '3', name: '布林带突破', market: '美股', timeframe: '4h', status: 'stopped' as const, pnl: -1.3 },
  { id: '4', name: '动量跟踪', market: 'A股', timeframe: '15m', status: 'running' as const, pnl: 3.7 },
  { id: '5', name: '配对交易', market: '加密货币', timeframe: '1d', status: 'stopped' as const, pnl: 0 },
]

function apiToDisplay(s: Strategy) {
  return {
    id: s.id,
    name: s.name,
    market: s.market,
    status: s.status,
    pnl: s.pnl,
  }
}

function StrategiesList() {
  const { data, isLoading, isError } = useStrategies()

  if (isLoading) return <LoadingSkeleton />

  const strategies = data
    ? data.map(apiToDisplay)
    : mockStrategies

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold">策略管理</h1>
        {isError && (
          <Badge variant="outline" className="text-muted-foreground">
            展示示例数据
          </Badge>
        )}
      </div>

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
                  <span>{s.market}</span>
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
    </div>
  )
}
