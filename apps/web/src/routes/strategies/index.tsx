import { createFileRoute } from '@tanstack/react-router'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'

export const Route = createFileRoute('/strategies/')({
  component: StrategiesList,
})

const mockStrategies = [
  { id: '1', name: 'SMA 交叉', market: 'A股', timeframe: '1d', status: 'running', pnl: '+5.2%' },
  { id: '2', name: 'RSI 均值回归', market: '加密货币', timeframe: '1h', status: 'running', pnl: '+12.8%' },
  { id: '3', name: '布林带突破', market: '美股', timeframe: '4h', status: 'stopped', pnl: '-1.3%' },
  { id: '4', name: '动量跟踪', market: 'A股', timeframe: '15m', status: 'running', pnl: '+3.7%' },
  { id: '5', name: '配对交易', market: '加密货币', timeframe: '1d', status: 'backtest', pnl: 'N/A' },
]

function StrategiesList() {
  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold">策略管理</h1>
      </div>

      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
        {mockStrategies.map((s) => (
          <Card key={s.id} className="cursor-pointer transition-colors hover:border-primary/50">
            <CardHeader className="flex flex-row items-center justify-between pb-2">
              <CardTitle className="text-base">{s.name}</CardTitle>
              <Badge
                variant={
                  s.status === 'running'
                    ? 'default'
                    : s.status === 'backtest'
                      ? 'secondary'
                      : 'outline'
                }
              >
                {s.status === 'running' ? '运行中' : s.status === 'backtest' ? '回测中' : '已停止'}
              </Badge>
            </CardHeader>
            <CardContent>
              <div className="flex items-center justify-between text-sm text-muted-foreground">
                <span>{s.market} · {s.timeframe}</span>
                <span
                  className={
                    s.pnl.startsWith('+')
                      ? 'font-medium text-green-500'
                      : s.pnl.startsWith('-')
                        ? 'font-medium text-red-500'
                        : ''
                  }
                >
                  {s.pnl}
                </span>
              </div>
            </CardContent>
          </Card>
        ))}
      </div>
    </div>
  )
}
