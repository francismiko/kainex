import { createFileRoute } from '@tanstack/react-router'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { PnlChart } from '@/components/charts/pnl-chart.lazy'
import { AllocationChart } from '@/components/charts/allocation-chart.lazy'
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table'
import { DollarSign, TrendingUp, Bot, AlertTriangle, ArrowUpRight, ArrowDownRight } from 'lucide-react'
import { formatCurrency, formatPercent, formatPnl } from '@/lib/format'
import { useChartHeight } from '@/hooks/use-mobile'

export const Route = createFileRoute('/')({
  component: Dashboard,
})

const mockPnlData = Array.from({ length: 30 }, (_, i) => ({
  time: `2026-02-${String(i + 1).padStart(2, '0')}`,
  value: 100000 + Math.random() * 20000 - 5000 + i * 500,
}))

const mockBenchmarkData = Array.from({ length: 30 }, (_, i) => ({
  time: `2026-02-${String(i + 1).padStart(2, '0')}`,
  value: 100000 + Math.random() * 10000 - 3000 + i * 300,
}))

const mockAllocationData = [
  { name: 'A \u80a1', value: 520000 },
  { name: '\u52a0\u5bc6\u8d27\u5e01', value: 410000 },
  { name: '\u7f8e\u80a1', value: 304567 },
]

const stats = [
  { title: '\u603b\u8d44\u4ea7', value: formatCurrency(1234567), change: formatPercent(2.34), icon: DollarSign, positive: true },
  { title: '\u4eca\u65e5\u6536\u76ca', value: formatCurrency(12345), change: formatPercent(0.98), icon: TrendingUp, positive: true },
  { title: '\u6d3b\u8dc3\u7b56\u7565', value: '5', change: '3 \u76c8\u5229 / 2 \u4e8f\u635f', icon: Bot, positive: true },
  { title: '\u98ce\u9669\u6562\u53e3', value: formatPercent(62), change: '\u4e2d\u7b49\u98ce\u9669', icon: AlertTriangle, positive: false },
]

const mockStrategies = [
  { name: 'SMA \u4ea4\u53c9', status: 'running' as const, pnl: '+5.2%', pnlValue: 26000, lastSignal: '\u4e70\u5165 BTC/USDT', signalTime: '10:32' },
  { name: 'RSI \u5747\u503c\u56de\u5f52', status: 'running' as const, pnl: '+12.8%', pnlValue: 64000, lastSignal: '\u5356\u51fa ETH/USDT', signalTime: '10:15' },
  { name: '\u5e03\u6797\u5e26\u7a81\u7834', status: 'stopped' as const, pnl: '-1.3%', pnlValue: -6500, lastSignal: '-', signalTime: '-' },
  { name: '\u52a8\u91cf\u8ddf\u8e2a', status: 'running' as const, pnl: '+3.7%', pnlValue: 18500, lastSignal: '\u4e70\u5165 AAPL', signalTime: '09:45' },
  { name: '\u914d\u5bf9\u4ea4\u6613', status: 'backtest' as const, pnl: 'N/A', pnlValue: 0, lastSignal: '-', signalTime: '-' },
]

const mockPositions = [
  { symbol: 'BTC/USDT', market: '\u52a0\u5bc6\u8d27\u5e01', side: '\u591a', qty: '0.5', avgPrice: 62340, currentPrice: 63150, pnlValue: 405, pnlPct: 0.65 },
  { symbol: 'ETH/USDT', market: '\u52a0\u5bc6\u8d27\u5e01', side: '\u591a', qty: '5.0', avgPrice: 3420, currentPrice: 3385, pnlValue: -175, pnlPct: -1.02 },
  { symbol: '\u8d35\u5dde\u8305\u53f0', market: 'A\u80a1', side: '\u591a', qty: '100', avgPrice: 1680, currentPrice: 1720, pnlValue: 4000, pnlPct: 2.38 },
  { symbol: 'AAPL', market: '\u7f8e\u80a1', side: '\u591a', qty: '50', avgPrice: 185.20, currentPrice: 188.50, pnlValue: 165, pnlPct: 1.78 },
  { symbol: 'TSLA', market: '\u7f8e\u80a1', side: '\u7a7a', qty: '30', avgPrice: 245.00, currentPrice: 242.30, pnlValue: 81, pnlPct: 1.10 },
]

const mockSignals = [
  { time: '10:32:15', strategy: 'SMA \u4ea4\u53c9', symbol: 'BTC/USDT', action: '\u4e70\u5165', price: '63,150' },
  { time: '10:15:42', strategy: 'RSI \u5747\u503c\u56de\u5f52', symbol: 'ETH/USDT', action: '\u5356\u51fa', price: '3,385' },
  { time: '09:45:03', strategy: '\u52a8\u91cf\u8ddf\u8e2a', symbol: 'AAPL', action: '\u4e70\u5165', price: '188.50' },
  { time: '09:30:17', strategy: 'SMA \u4ea4\u53c9', symbol: '\u8d35\u5dde\u8305\u53f0', action: '\u4e70\u5165', price: '1,720' },
  { time: '09:15:28', strategy: '\u52a8\u91cf\u8ddf\u8e2a', symbol: 'TSLA', action: '\u5356\u51fa', price: '242.30' },
  { time: '08:55:11', strategy: 'RSI \u5747\u503c\u56de\u5f52', symbol: 'BTC/USDT', action: '\u4e70\u5165', price: '62,800' },
  { time: '08:32:44', strategy: 'SMA \u4ea4\u53c9', symbol: 'ETH/USDT', action: '\u4e70\u5165', price: '3,410' },
  { time: '08:15:59', strategy: '\u52a8\u91cf\u8ddf\u8e2a', symbol: 'AAPL', action: '\u5356\u51fa', price: '186.00' },
  { time: '08:01:23', strategy: 'RSI \u5747\u503c\u56de\u5f52', symbol: '\u8d35\u5dde\u8305\u53f0', action: '\u4e70\u5165', price: '1,690' },
  { time: '07:45:06', strategy: 'SMA \u4ea4\u53c9', symbol: 'TSLA', action: '\u5356\u51fa', price: '244.10' },
]

function Dashboard() {
  const pnlChartHeight = useChartHeight(350, 250)
  const allocationChartHeight = useChartHeight(300, 250)

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold">{'\u603b\u89c8'}</h1>

      {/* Stats cards -- 2 cols on mobile, 4 on desktop */}
      <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
        {stats.map((stat) => (
          <Card key={stat.title}>
            <CardHeader className="flex flex-row items-center justify-between pb-2">
              <CardTitle className="text-sm font-medium text-muted-foreground">
                {stat.title}
              </CardTitle>
              <stat.icon className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              <div className="text-xl font-bold sm:text-2xl">{stat.value}</div>
              <p
                className={`text-xs ${stat.positive ? 'text-profit' : 'text-yellow-500'}`}
              >
                {stat.change}
              </p>
            </CardContent>
          </Card>
        ))}
      </div>

      {/* Strategy status panel -- horizontal scroll on mobile, hide non-critical columns */}
      <Card>
        <CardHeader>
          <CardTitle>{'\u7b56\u7565\u5b9e\u65f6\u72b6\u6001'}</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="overflow-x-auto">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>{'\u7b56\u7565'}</TableHead>
                  <TableHead>{'\u72b6\u6001'}</TableHead>
                  <TableHead className="text-right">{'\u6536\u76ca'}</TableHead>
                  <TableHead className="hidden sm:table-cell">{'\u6700\u8fd1\u4fe1\u53f7'}</TableHead>
                  <TableHead className="hidden sm:table-cell text-right">{'\u65f6\u95f4'}</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {mockStrategies.map((s) => {
                  const pnl = formatPnl(s.pnlValue)
                  return (
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
                          {s.status === 'running' ? '\u8fd0\u884c\u4e2d' : s.status === 'backtest' ? '\u56de\u6d4b\u4e2d' : '\u5df2\u505c\u6b62'}
                        </Badge>
                      </TableCell>
                      <TableCell className={`text-right font-mono ${s.pnlValue === 0 ? 'text-muted-foreground' : pnl.className}`}>
                        {s.pnlValue === 0 ? s.pnl : `${pnl.text} (${s.pnl})`}
                      </TableCell>
                      <TableCell className="hidden sm:table-cell text-muted-foreground">{s.lastSignal}</TableCell>
                      <TableCell className="hidden sm:table-cell text-right text-muted-foreground">{s.signalTime}</TableCell>
                    </TableRow>
                  )
                })}
              </TableBody>
            </Table>
          </div>
        </CardContent>
      </Card>

      {/* Positions + Allocation: 2 cols on desktop, stacked on mobile */}
      <div className="grid gap-4 lg:grid-cols-2">
        {/* Top 5 positions */}
        <Card>
          <CardHeader>
            <CardTitle>{'\u6301\u4ed3 Top 5'}</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="overflow-x-auto">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>{'\u6807\u7684'}</TableHead>
                    <TableHead>{'\u65b9\u5411'}</TableHead>
                    <TableHead className="text-right">{'\u73b0\u4ef7'}</TableHead>
                    <TableHead className="text-right">{'\u6d6e\u76c8'}</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {mockPositions.map((p) => {
                    const pnl = formatPnl(p.pnlValue)
                    return (
                      <TableRow key={p.symbol}>
                        <TableCell>
                          <div className="font-medium">{p.symbol}</div>
                          <div className="text-xs text-muted-foreground">{p.market}</div>
                        </TableCell>
                        <TableCell>
                          <Badge variant={p.side === '\u591a' ? 'default' : 'destructive'} className="text-xs">
                            {p.side}
                          </Badge>
                        </TableCell>
                        <TableCell className="text-right font-mono">{formatCurrency(p.currentPrice)}</TableCell>
                        <TableCell className={`text-right font-mono ${pnl.className}`}>
                          <div>{pnl.text}</div>
                          <div className="text-xs">{formatPercent(p.pnlPct)}</div>
                        </TableCell>
                      </TableRow>
                    )
                  })}
                </TableBody>
              </Table>
            </div>
          </CardContent>
        </Card>

        {/* Asset allocation donut chart */}
        <Card>
          <CardHeader>
            <CardTitle>{'\u8d44\u4ea7\u5206\u5e03'}</CardTitle>
          </CardHeader>
          <CardContent>
            <AllocationChart data={mockAllocationData} height={allocationChartHeight} />
          </CardContent>
        </Card>
      </div>

      {/* Recent signals feed */}
      <Card>
        <CardHeader>
          <CardTitle>{'\u6700\u65b0\u4ea4\u6613\u4fe1\u53f7'}</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-3">
            {mockSignals.map((sig, i) => (
              <div key={i} className="flex items-center gap-3 text-sm">
                <div className="flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-muted">
                  {sig.action === '\u4e70\u5165' ? (
                    <ArrowUpRight className="h-3.5 w-3.5 text-profit" />
                  ) : (
                    <ArrowDownRight className="h-3.5 w-3.5 text-loss" />
                  )}
                </div>
                <div className="min-w-0 flex-1">
                  <div className="flex items-center gap-2">
                    <span className={`font-medium ${sig.action === '\u4e70\u5165' ? 'text-profit' : 'text-loss'}`}>
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

      {/* PnL curve with benchmark */}
      <Card>
        <CardHeader>
          <CardTitle>{'\u6536\u76ca\u66f2\u7ebf'}</CardTitle>
        </CardHeader>
        <CardContent>
          <PnlChart data={mockPnlData} benchmark={mockBenchmarkData} height={pnlChartHeight} />
        </CardContent>
      </Card>
    </div>
  )
}
