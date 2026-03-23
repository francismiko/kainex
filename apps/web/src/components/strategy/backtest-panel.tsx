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
import { PnlChart } from '@/components/charts/pnl-chart'
import { DrawdownChart } from '@/components/charts/drawdown-chart'
import { MonthlyHeatmap } from '@/components/charts/monthly-heatmap'
import { formatPercent, formatNumber, formatCurrency } from '@/lib/format'
import type { BacktestResult } from '@/types/strategy'

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

export function BacktestPanel({ result }: BacktestPanelProps) {
  const { equity_curve, trades, metrics } = result

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
          <PnlChart data={equity_curve} height={280} />
        </CardContent>
      </Card>

      {/* Drawdown chart */}
      <Card>
        <CardHeader className="pb-2">
          <CardTitle className="text-sm">水下回撤</CardTitle>
        </CardHeader>
        <CardContent>
          <DrawdownChart equityCurve={equity_curve} height={180} />
        </CardContent>
      </Card>

      {/* Monthly heatmap */}
      <Card>
        <CardHeader className="pb-2">
          <CardTitle className="text-sm">月度收益</CardTitle>
        </CardHeader>
        <CardContent>
          <MonthlyHeatmap equityCurve={equity_curve} height={200} />
        </CardContent>
      </Card>

      {/* Trade table */}
      <Card>
        <CardHeader className="pb-2">
          <CardTitle className="text-sm">交易记录</CardTitle>
        </CardHeader>
        <CardContent>
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
        </CardContent>
      </Card>
    </div>
  )
}
