import { useMemo } from 'react'
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
import { PnlChart } from '@/components/charts/pnl-chart.lazy'
import { DrawdownChart } from '@/components/charts/drawdown-chart.lazy'
import { MonthlyHeatmap } from '@/components/charts/monthly-heatmap.lazy'
import { PriceChart, type ChartMarker } from '@/components/charts/price-chart'
import { formatPercent, formatNumber, formatCurrency } from '@/lib/format'
import { useChartHeight } from '@/hooks/use-mobile'
import type { BacktestResult, BacktestTrade } from '@/types/strategy'
import type { CandlestickData, Time } from 'lightweight-charts'

interface BacktestPanelProps {
  result: BacktestResult
}

function MetricCard({ label, value, colored }: { label: string; value: string; colored?: boolean }) {
  const isNegative = colored && value.startsWith('-')
  return (
    <Card>
      <CardContent className="p-4">
        <p className="text-xs text-muted-foreground">{label}</p>
        <p
          className="text-lg font-bold mt-1"
          style={colored ? { color: isNegative ? 'var(--color-loss)' : 'var(--color-profit)' } : undefined}
        >
          {value}
        </p>
      </CardContent>
    </Card>
  )
}

function tradesToMarkers(trades: BacktestTrade[]): ChartMarker[] {
  const markers: ChartMarker[] = []
  for (const t of trades) {
    // Entry marker
    markers.push({
      time: t.entry_time || t.timestamp,
      position: t.side === 'buy' ? 'belowBar' : 'aboveBar',
      color: t.side === 'buy' ? '#22c55e' : '#ef4444',
      shape: t.side === 'buy' ? 'arrowUp' : 'arrowDown',
      text: t.side === 'buy' ? `买 ${formatCurrency(t.entry_price || t.price)}` : `卖 ${formatCurrency(t.entry_price || t.price)}`,
    })
    // Exit marker (if exists)
    if (t.exit_time && t.exit_price) {
      markers.push({
        time: t.exit_time,
        position: t.side === 'buy' ? 'aboveBar' : 'belowBar',
        color: t.pnl >= 0 ? '#22c55e' : '#ef4444',
        shape: 'circle',
        text: `平 ${formatCurrency(t.exit_price)}`,
      })
    }
  }
  return markers
}

function equityCurveToCandlestickData(
  equityCurve: { time: string; value: number }[],
): CandlestickData<Time>[] {
  return equityCurve.map((point, i) => {
    const prev = i > 0 ? equityCurve[i - 1].value : point.value
    const open = prev
    const close = point.value
    const high = Math.max(open, close) * 1.001
    const low = Math.min(open, close) * 0.999
    return {
      time: point.time as unknown as Time,
      open,
      high,
      low,
      close,
    }
  })
}

export function BacktestPanel({ result }: BacktestPanelProps) {
  const { equity_curve, trades, metrics } = result
  const equityHeight = useChartHeight(280, 220)
  const drawdownHeight = useChartHeight(180, 150)
  const heatmapHeight = useChartHeight(200, 160)
  const tradeChartHeight = useChartHeight(350, 280)

  const tradeMarkers = useMemo(() => tradesToMarkers(trades), [trades])
  const candlestickData = useMemo(
    () => equityCurveToCandlestickData(equity_curve),
    [equity_curve],
  )

  return (
    <div className="space-y-4">
      {/* Metrics cards */}
      <div className="grid gap-3 grid-cols-2 sm:grid-cols-4 lg:grid-cols-7">
        <MetricCard label="总收益" value={formatPercent(metrics.total_return)} colored />
        <MetricCard label="年化收益" value={formatPercent(metrics.annual_return)} colored />
        <MetricCard label="夏普比率" value={formatNumber(metrics.sharpe)} />
        <MetricCard label="最大回撤" value={formatPercent(metrics.max_drawdown)} colored />
        <MetricCard label="胜率" value={formatPercent(metrics.win_rate)} />
        <MetricCard label="盈亏比" value={formatNumber(metrics.profit_factor)} />
        <MetricCard label="交易次数" value={String(metrics.trade_count)} />
      </div>

      {/* Equity curve */}
      <Card>
        <CardHeader className="pb-2">
          <CardTitle className="text-sm">收益曲线</CardTitle>
        </CardHeader>
        <CardContent>
          <PnlChart data={equity_curve} height={equityHeight} />
        </CardContent>
      </Card>

      {/* Trade markers on price chart */}
      {trades.length > 0 && (
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm">交易标注</CardTitle>
          </CardHeader>
          <CardContent>
            <PriceChart
              data={candlestickData}
              height={tradeChartHeight}
              markers={tradeMarkers}
            />
          </CardContent>
        </Card>
      )}

      {/* Drawdown chart */}
      <Card>
        <CardHeader className="pb-2">
          <CardTitle className="text-sm">水下回撤</CardTitle>
        </CardHeader>
        <CardContent>
          <DrawdownChart equityCurve={equity_curve} height={drawdownHeight} />
        </CardContent>
      </Card>

      {/* Monthly heatmap */}
      <Card>
        <CardHeader className="pb-2">
          <CardTitle className="text-sm">月度收益</CardTitle>
        </CardHeader>
        <CardContent>
          <MonthlyHeatmap equityCurve={equity_curve} height={heatmapHeight} />
        </CardContent>
      </Card>

      {/* Trade table */}
      <Card>
        <CardHeader className="pb-2">
          <CardTitle className="text-sm">交易记录</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="overflow-x-auto">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>时间</TableHead>
                  <TableHead>标的</TableHead>
                  <TableHead>方向</TableHead>
                  <TableHead className="text-right">价格</TableHead>
                  <TableHead className="text-right">数量</TableHead>
                  <TableHead className="text-right">盈亏</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {trades.length === 0 ? (
                  <TableRow>
                    <TableCell colSpan={6} className="text-center text-muted-foreground">
                      暂无交易记录
                    </TableCell>
                  </TableRow>
                ) : (
                  trades.map((trade) => (
                    <TableRow key={trade.id}>
                      <TableCell className="text-muted-foreground">{trade.timestamp}</TableCell>
                      <TableCell>{trade.symbol}</TableCell>
                      <TableCell>
                        <Badge variant={trade.side === 'buy' ? 'default' : 'outline'}>
                          {trade.side === 'buy' ? '买入' : '卖出'}
                        </Badge>
                      </TableCell>
                      <TableCell className="text-right">{formatCurrency(trade.price)}</TableCell>
                      <TableCell className="text-right">{formatNumber(trade.quantity, 4)}</TableCell>
                      <TableCell
                        className="text-right font-medium"
                        style={{ color: trade.pnl >= 0 ? 'var(--color-profit)' : 'var(--color-loss)' }}
                      >
                        {formatCurrency(trade.pnl)}
                      </TableCell>
                    </TableRow>
                  ))
                )}
              </TableBody>
            </Table>
          </div>
        </CardContent>
      </Card>
    </div>
  )
}
