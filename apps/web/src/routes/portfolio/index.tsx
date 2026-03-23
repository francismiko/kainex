import { createFileRoute } from '@tanstack/react-router'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { PnlChart } from '@/components/charts/pnl-chart.lazy'
import { LoadingSkeleton } from '@/components/shared/loading-skeleton'
import { usePortfolioSummary, usePositions } from '@/hooks/use-api'
import { formatNumber } from '@/lib/format'
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table'

export const Route = createFileRoute('/portfolio/')({
  component: Portfolio,
})

const mockPnlData = Array.from({ length: 60 }, (_, i) => ({
  time: `2026-01-${String((i % 30) + 1).padStart(2, '0')}`,
  value: 100000 + Math.random() * 30000 - 10000 + i * 300,
}))

const mockPositions = [
  { symbol: 'BTC/USDT', market: '加密货币', side: '多' as const, qty: '0.5', avgPrice: '62,340', currentPrice: '63,150', unrealizedPnl: 405, unrealizedPct: 0.65 },
  { symbol: 'ETH/USDT', market: '加密货币', side: '多' as const, qty: '5.0', avgPrice: '3,420', currentPrice: '3,385', unrealizedPnl: -175, unrealizedPct: -1.02 },
  { symbol: '贵州茅台', market: 'A股', side: '多' as const, qty: '100', avgPrice: '1,680', currentPrice: '1,720', unrealizedPnl: 4000, unrealizedPct: 2.38 },
  { symbol: 'AAPL', market: '美股', side: '多' as const, qty: '50', avgPrice: '185.20', currentPrice: '188.50', unrealizedPnl: 165, unrealizedPct: 1.78 },
  { symbol: 'TSLA', market: '美股', side: '空' as const, qty: '30', avgPrice: '245.00', currentPrice: '242.30', unrealizedPnl: 81, unrealizedPct: 1.10 },
  { symbol: 'SOL/USDT', market: '加密货币', side: '多' as const, qty: '20', avgPrice: '142.50', currentPrice: '145.80', unrealizedPnl: 66, unrealizedPct: 2.32 },
  { symbol: '宁德时代', market: 'A股', side: '多' as const, qty: '200', avgPrice: '218.00', currentPrice: '215.50', unrealizedPnl: -500, unrealizedPct: -1.15 },
  { symbol: 'NVDA', market: '美股', side: '多' as const, qty: '25', avgPrice: '850.00', currentPrice: '872.30', unrealizedPnl: 557.5, unrealizedPct: 2.62 },
]

function apiPositionsToDisplay(positions: { symbol: string; side: string; quantity: number; entryPrice: number; currentPrice: number; unrealizedPnl: number }[]) {
  return positions.map((p) => ({
    symbol: p.symbol,
    market: '-',
    side: (p.side === 'long' ? '多' : '空') as '多' | '空',
    qty: String(p.quantity),
    avgPrice: formatNumber(p.entryPrice),
    currentPrice: formatNumber(p.currentPrice),
    unrealizedPnl: p.unrealizedPnl,
    unrealizedPct: p.entryPrice ? ((p.currentPrice - p.entryPrice) / p.entryPrice) * 100 : 0,
  }))
}

function Portfolio() {
  const summaryQuery = usePortfolioSummary()
  const positionsQuery = usePositions()

  if (summaryQuery.isLoading && positionsQuery.isLoading) return <LoadingSkeleton />

  const positions = positionsQuery.data
    ? apiPositionsToDisplay(positionsQuery.data)
    : mockPositions

  const totalUnrealized = positions.reduce((sum, p) => sum + p.unrealizedPnl, 0)

  const summaryData = summaryQuery.data
  const usingMock = !summaryData && !positionsQuery.data

  return (
    <div className="space-y-6">
      <div className="flex items-center gap-3">
        <h1 className="text-2xl font-bold">持仓组合</h1>
        {usingMock && (
          <Badge variant="outline" className="text-muted-foreground">
            展示示例数据
          </Badge>
        )}
      </div>

      <div className="grid gap-4 md:grid-cols-4">
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground">总资产</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
              {summaryData ? formatNumber(summaryData.totalValue) : '¥1,234,567'}
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground">可用资金</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
              {summaryData ? formatNumber(summaryData.cash) : '¥456,789'}
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground">今日盈亏</CardTitle>
          </CardHeader>
          <CardContent>
            <div className={`text-2xl font-bold ${(summaryData?.dailyPnl ?? 1200) >= 0 ? 'text-profit' : 'text-loss'}`}>
              {summaryData ? (summaryData.dailyPnl >= 0 ? '+' : '') + formatNumber(summaryData.dailyPnl) : '+1,200'}
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground">浮动盈亏</CardTitle>
          </CardHeader>
          <CardContent>
            <div className={`text-2xl font-bold ${totalUnrealized >= 0 ? 'text-profit' : 'text-loss'}`}>
              {totalUnrealized >= 0 ? '+' : ''}{totalUnrealized.toLocaleString()}
            </div>
          </CardContent>
        </Card>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>累计收益</CardTitle>
        </CardHeader>
        <CardContent>
          <PnlChart data={mockPnlData} height={350} />
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>当前持仓</CardTitle>
        </CardHeader>
        <CardContent>
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>标的</TableHead>
                <TableHead>市场</TableHead>
                <TableHead>方向</TableHead>
                <TableHead className="text-right">数量</TableHead>
                <TableHead className="text-right">均价</TableHead>
                <TableHead className="text-right">现价</TableHead>
                <TableHead className="text-right">浮盈</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {positions.map((p) => (
                <TableRow key={p.symbol}>
                  <TableCell className="font-medium">{p.symbol}</TableCell>
                  <TableCell className="text-muted-foreground">{p.market}</TableCell>
                  <TableCell>
                    <Badge variant={p.side === '多' ? 'default' : 'destructive'} className="text-xs">
                      {p.side}
                    </Badge>
                  </TableCell>
                  <TableCell className="text-right font-mono">{p.qty}</TableCell>
                  <TableCell className="text-right font-mono">{p.avgPrice}</TableCell>
                  <TableCell className="text-right font-mono">{p.currentPrice}</TableCell>
                  <TableCell className={`text-right font-mono font-medium ${p.unrealizedPnl >= 0 ? 'text-profit' : 'text-loss'}`}>
                    <div>{p.unrealizedPnl >= 0 ? '+' : ''}{p.unrealizedPnl.toLocaleString()}</div>
                    <div className="text-xs">{p.unrealizedPct >= 0 ? '+' : ''}{p.unrealizedPct.toFixed(2)}%</div>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </CardContent>
      </Card>
    </div>
  )
}
