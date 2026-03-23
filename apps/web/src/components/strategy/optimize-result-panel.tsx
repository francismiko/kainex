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
import { formatPercent, formatNumber } from '@/lib/format'
import type { OptimizeResponse } from '@/types/strategy'
import ReactECharts from 'echarts-for-react'
import type { EChartsOption } from 'echarts'

interface OptimizeResultPanelProps {
  data: OptimizeResponse
  metric: string
}

const METRIC_LABELS: Record<string, string> = {
  sharpe_ratio: '夏普比率',
  total_return: '总收益',
  win_rate: '胜率',
  max_drawdown: '最大回撤',
}

function metricKey(metric: string): keyof OptimizeResponse['results'][0]['metrics'] {
  const map: Record<string, keyof OptimizeResponse['results'][0]['metrics']> = {
    sharpe_ratio: 'sharpe',
    total_return: 'total_return',
    win_rate: 'win_rate',
    max_drawdown: 'max_drawdown',
  }
  return map[metric] ?? 'sharpe'
}

function formatMetricValue(key: string, value: number): string {
  if (key === 'sharpe_ratio') return formatNumber(value)
  return formatPercent(value)
}

export function OptimizeResultPanel({ data, metric }: OptimizeResultPanelProps) {
  const best = data.results[0]
  const paramKeys = best ? Object.keys(best.parameters) : []
  const showHeatmap = paramKeys.length === 2

  return (
    <div className="space-y-4">
      {/* Best parameters card */}
      {best && (
        <Card className="border-primary/50 bg-primary/5">
          <CardHeader className="pb-2">
            <CardTitle className="flex items-center gap-2 text-sm">
              <Badge variant="default">最佳参数</Badge>
              <span className="text-muted-foreground">
                共测试 {data.total_combinations} 个组合
              </span>
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="flex flex-wrap gap-4">
              {Object.entries(data.best_parameters).map(([key, value]) => (
                <div key={key} className="flex items-baseline gap-1.5">
                  <span className="text-sm text-muted-foreground font-mono">{key}:</span>
                  <span className="text-lg font-bold font-mono">{String(value)}</span>
                </div>
              ))}
              <div className="ml-auto flex items-baseline gap-1.5">
                <span className="text-sm text-muted-foreground">
                  {METRIC_LABELS[metric] ?? metric}:
                </span>
                <span className="text-lg font-bold text-primary">
                  {formatMetricValue(metric, best.metrics[metricKey(metric)])}
                </span>
              </div>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Heatmap for 2-parameter case */}
      {showHeatmap && (
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm">参数热力图</CardTitle>
          </CardHeader>
          <CardContent>
            <ParameterHeatmap data={data} metric={metric} paramKeys={paramKeys} />
          </CardContent>
        </Card>
      )}

      {/* Results ranking table */}
      <Card>
        <CardHeader className="pb-2">
          <CardTitle className="text-sm">优化结果排名</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="overflow-x-auto">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead className="w-12">排名</TableHead>
                  {paramKeys.map((k) => (
                    <TableHead key={k} className="font-mono">{k}</TableHead>
                  ))}
                  <TableHead className="text-right">夏普比率</TableHead>
                  <TableHead className="text-right">总收益</TableHead>
                  <TableHead className="text-right">最大回撤</TableHead>
                  <TableHead className="text-right">胜率</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {data.results.map((item) => (
                  <TableRow
                    key={item.rank}
                    className={item.rank === 1 ? 'bg-primary/5 font-medium' : ''}
                  >
                    <TableCell>
                      {item.rank === 1 ? (
                        <Badge variant="default">1</Badge>
                      ) : (
                        <span className="text-muted-foreground">{item.rank}</span>
                      )}
                    </TableCell>
                    {paramKeys.map((k) => (
                      <TableCell key={k} className="font-mono">
                        {String(item.parameters[k])}
                      </TableCell>
                    ))}
                    <TableCell className="text-right font-mono">
                      {formatNumber(item.metrics.sharpe)}
                    </TableCell>
                    <TableCell
                      className="text-right font-mono"
                      style={{
                        color: item.metrics.total_return >= 0
                          ? 'var(--color-profit)'
                          : 'var(--color-loss)',
                      }}
                    >
                      {formatPercent(item.metrics.total_return)}
                    </TableCell>
                    <TableCell
                      className="text-right font-mono"
                      style={{ color: 'var(--color-loss)' }}
                    >
                      {formatPercent(item.metrics.max_drawdown)}
                    </TableCell>
                    <TableCell className="text-right font-mono">
                      {formatPercent(item.metrics.win_rate)}
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </div>
        </CardContent>
      </Card>
    </div>
  )
}

function ParameterHeatmap({
  data,
  metric,
  paramKeys,
}: {
  data: OptimizeResponse
  metric: string
  paramKeys: string[]
}) {
  const option = useMemo<EChartsOption>(() => {
    const mk = metricKey(metric)
    const xKey = paramKeys[0]
    const yKey = paramKeys[1]

    // Collect unique values for each axis
    const xVals = [...new Set(data.results.map((r) => Number(r.parameters[xKey])))].sort((a, b) => a - b)
    const yVals = [...new Set(data.results.map((r) => Number(r.parameters[yKey])))].sort((a, b) => a - b)

    const heatmapData: [number, number, number][] = []
    for (const r of data.results) {
      const xi = xVals.indexOf(Number(r.parameters[xKey]))
      const yi = yVals.indexOf(Number(r.parameters[yKey]))
      const val = r.metrics[mk]
      heatmapData.push([xi, yi, Math.round(val * 100) / 100])
    }

    const values = heatmapData.map((d) => d[2])
    const minVal = Math.min(...values)
    const maxVal = Math.max(...values)

    return {
      backgroundColor: 'transparent',
      tooltip: {
        formatter: (params: unknown) => {
          const p = params as { value: [number, number, number] }
          return `${xKey}=${xVals[p.value[0]]}, ${yKey}=${yVals[p.value[1]]}<br/>${METRIC_LABELS[metric] ?? metric}: ${p.value[2]}`
        },
      },
      xAxis: {
        type: 'category',
        data: xVals.map(String),
        name: xKey,
        nameLocation: 'center',
        nameGap: 30,
        axisLine: { lineStyle: { color: 'rgba(255, 255, 255, 0.08)' } },
        axisLabel: { color: 'var(--color-muted-foreground, #9ca3af)', fontSize: 11 },
      },
      yAxis: {
        type: 'category',
        data: yVals.map(String),
        name: yKey,
        nameLocation: 'center',
        nameGap: 50,
        axisLine: { lineStyle: { color: 'rgba(255, 255, 255, 0.08)' } },
        axisLabel: { color: 'var(--color-muted-foreground, #9ca3af)', fontSize: 11 },
      },
      visualMap: {
        min: minVal,
        max: maxVal,
        calculable: false,
        orient: 'horizontal',
        left: 'center',
        bottom: 0,
        inRange: {
          color: ['#ef4444', '#fca5a5', '#fef2f2', '#f0fdf4', '#86efac', '#22c55e'],
        },
        textStyle: { color: 'var(--color-muted-foreground, #9ca3af)' },
      },
      series: [
        {
          type: 'heatmap',
          data: heatmapData,
          label: {
            show: true,
            color: 'var(--color-foreground, #e5e7eb)',
            fontSize: 10,
            formatter: (params: unknown) => {
              const p = params as { value: [number, number, number] }
              return String(p.value[2])
            },
          },
          emphasis: {
            itemStyle: { shadowBlur: 6, shadowColor: 'rgba(0, 0, 0, 0.3)' },
          },
        },
      ],
      grid: { left: 70, right: 20, top: 10, bottom: 60 },
    }
  }, [data, metric, paramKeys])

  return <ReactECharts option={option} style={{ height: 300 }} />
}
