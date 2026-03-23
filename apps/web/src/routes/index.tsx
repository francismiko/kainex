import { createFileRoute } from '@tanstack/react-router'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { PnlChart } from '@/components/charts/pnl-chart.lazy'
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table'
import { DollarSign, TrendingUp, Bot, AlertTriangle, ArrowUpRight, ArrowDownRight } from 'lucide-react'

export const Route = createFileRoute('/')({
  component: Dashboard,
})

const mockPnlData = Array.from({ length: 30 }, (_, i) => ({
  time: `2026-02-${String(i + 1).padStart(2, '0')}`,
  value: 100000 + Math.random() * 20000 - 5000 + i * 500,
}))

const stats = [
  { title: '总资产', value: '\u00a5 1,234,567', change: '+2.34%', icon: DollarSign, positive: true },
  { title: '今日收益', value: '\u00a5 12,345', change: '+0.98%', icon: TrendingUp, positive: true },
  { title: '活跃策略', value: '5', change: '3 盈利 / 2 亏损', icon: Bot, positive: true },
  { title: '风险敞口', value: '62%', change: '中等风险', icon: AlertTriangle, positive: false },
]

const mockStrategies = [
  { name: 'SMA 交叉', status: 'running' as const, pnl: '+5.2%', pnlValue: 26000, lastSignal: '买入 BTC/USDT', signalTime: '10:32' },
  { name: 'RSI 均值回归', status: 'running' as const, pnl: '+12.8%', pnlValue: 64000, lastSignal: '卖出 ETH/USDT', signalTime: '10:15' },
  { name: '布林带突破', status: 'stopped' as const, pnl: '-1.3%', pnlValue: -6500, lastSignal: '-', signalTime: '-' },
  { name: '动量跟踪', status: 'running' as const, pnl: '+3.7%', pnlValue: 18500, lastSignal: '买入 AAPL', signalTime: '09:45' },
  { name: '配对交易', status: 'backtest' as const, pnl: 'N/A', pnlValue: 0, lastSignal: '-', signalTime: '-' },
]

const mockPositions = [
  { symbol: 'BTC/USDT', market: '加密货币', side: '多', qty: '0.5', avgPrice: '62,340', currentPrice: '63,150', pnl: '+405.00', pnlPct: '+0.65%' },
  { symbol: 'ETH/USDT', market: '加密货币', side: '多', qty: '5.0', avgPrice: '3,420', currentPrice: '3,385', pnl: '-175.00', pnlPct: '-1.02%' },
  { symbol: '贵州茅台', market: 'A股', side: '多', qty: '100', avgPrice: '1,680', currentPrice: '1,720', pnl: '+4,000', pnlPct: '+2.38%' },
  { symbol: 'AAPL', market: '美股', side: '多', qty: '50', avgPrice: '185.20', currentPrice: '188.50', pnl: '+165.00', pnlPct: '+1.78%' },
  { symbol: 'TSLA', market: '美股', side: '空', qty: '30', avgPrice: '245.00', currentPrice: '242.30', pnl: '+81.00', pnlPct: '+1.10%' },
]

const mockSignals = [
  { time: '10:32:15', strategy: 'SMA 交叉', symbol: 'BTC/USDT', action: '买入', price: '63,150' },
  { time: '10:15:42', strategy: 'RSI 均值回归', symbol: 'ETH/USDT', action: '卖出', price: '3,385' },
  { time: '09:45:03', strategy: '动量跟踪', symbol: 'AAPL', action: '买入', price: '188.50' },
  { time: '09:30:17', strategy: 'SMA 交叉', symbol: '贵州茅台', action: '买入', price: '1,720' },
  { time: '09:15:28', strategy: '动量跟踪', symbol: 'TSLA', action: '卖出', price: '242.30' },
  { time: '08:55:11', strategy: 'RSI 均值回归', symbol: 'BTC/USDT', action: '买入', price: '62,800' },
  { time: '08:32:44', strategy: 'SMA 交叉', symbol: 'ETH/USDT', action: '买入', price: '3,410' },
  { time: '08:15:59', strategy: '动量跟踪', symbol: 'AAPL', action: '卖出', price: '186.00' },
  { time: '08:01:23', strategy: 'RSI 均值回归', symbol: '贵州茅台', action: '买入', price: '1,690' },
  { time: '07:45:06', strategy: 'SMA 交叉', symbol: 'TSLA', action: '卖出', price: '244.10' },
]

function Dashboard() {
  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold">总览</h1>

      {/* Stats cards */}
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
        {stats.map((stat) => (
          <Card key={stat.title}>
            <CardHeader className="flex flex-row items-center justify-between pb-2">
              <CardTitle className="text-sm font-medium text-muted-foreground">
                {stat.title}
              </CardTitle>
              <stat.icon className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{stat.value}</div>
              <p
                className={`text-xs ${stat.positive ? 'text-profit' : 'text-yellow-500'}`}
              >
                {stat.change}
              </p>
            </CardContent>
          </Card>
        ))}
      </div>

      {/* Strategy status panel */}
      <Card>
        <CardHeader>
          <CardTitle>策略实时状态</CardTitle>
        </CardHeader>
        <CardContent>
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>策略</TableHead>
                <TableHead>状态</TableHead>
                <TableHead className="text-right">收益</TableHead>
                <TableHead>最近信号</TableHead>
                <TableHead className="text-right">时间</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {mockStrategies.map((s) => (
                <TableRow key={s.name}>
                  <TableCell className="font-medium">{s.name}</TableCell>
                  <TableCell>
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
                  </TableCell>
                  <TableCell className={`text-right font-mono ${s.pnl.startsWith('+') ? 'text-profit' : s.pnl.startsWith('-') ? 'text-loss' : 'text-muted-foreground'}`}>
                    {s.pnl}
                  </TableCell>
                  <TableCell className="text-muted-foreground">{s.lastSignal}</TableCell>
                  <TableCell className="text-right text-muted-foreground">{s.signalTime}</TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </CardContent>
      </Card>

      <div className="grid gap-4 lg:grid-cols-2">
        {/* Top 5 positions */}
        <Card>
          <CardHeader>
            <CardTitle>持仓 Top 5</CardTitle>
          </CardHeader>
          <CardContent>
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>标的</TableHead>
                  <TableHead>方向</TableHead>
                  <TableHead className="text-right">现价</TableHead>
                  <TableHead className="text-right">浮盈</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {mockPositions.map((p) => (
                  <TableRow key={p.symbol}>
                    <TableCell>
                      <div className="font-medium">{p.symbol}</div>
                      <div className="text-xs text-muted-foreground">{p.market}</div>
                    </TableCell>
                    <TableCell>
                      <Badge variant={p.side === '多' ? 'default' : 'destructive'} className="text-xs">
                        {p.side}
                      </Badge>
                    </TableCell>
                    <TableCell className="text-right font-mono">{p.currentPrice}</TableCell>
                    <TableCell className={`text-right font-mono ${p.pnl.startsWith('+') ? 'text-profit' : 'text-loss'}`}>
                      <div>{p.pnl}</div>
                      <div className="text-xs">{p.pnlPct}</div>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </CardContent>
        </Card>

        {/* Recent signals feed */}
        <Card>
          <CardHeader>
            <CardTitle>最新交易信号</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-3">
              {mockSignals.map((sig, i) => (
                <div key={i} className="flex items-center gap-3 text-sm">
                  <div className="flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-muted">
                    {sig.action === '买入' ? (
                      <ArrowUpRight className="h-3.5 w-3.5 text-profit" />
                    ) : (
                      <ArrowDownRight className="h-3.5 w-3.5 text-loss" />
                    )}
                  </div>
                  <div className="min-w-0 flex-1">
                    <div className="flex items-center gap-2">
                      <span className={`font-medium ${sig.action === '买入' ? 'text-profit' : 'text-loss'}`}>
                        {sig.action}
                      </span>
                      <span className="font-medium">{sig.symbol}</span>
                      <span className="text-muted-foreground">@ {sig.price}</span>
                    </div>
                    <div className="text-xs text-muted-foreground">
                      {sig.strategy} -- {sig.time}
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      </div>

      {/* PnL curve */}
      <Card>
        <CardHeader>
          <CardTitle>收益曲线</CardTitle>
        </CardHeader>
        <CardContent>
          <PnlChart data={mockPnlData} height={350} />
        </CardContent>
      </Card>
    </div>
  )
}
