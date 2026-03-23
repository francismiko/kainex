import { useMemo } from 'react'
import ReactECharts from 'echarts-for-react'
import type { EChartsOption } from 'echarts'

interface PnlChartProps {
  data: { time: string; value: number }[]
  title?: string
  height?: number
}

export function PnlChart({ data, title, height = 300 }: PnlChartProps) {
  const option = useMemo<EChartsOption>(
    () => ({
      backgroundColor: 'transparent',
      title: title
        ? {
            text: title,
            textStyle: { color: 'var(--color-muted-foreground, #9ca3af)', fontSize: 14 },
            left: 'center',
          }
        : undefined,
      tooltip: {
        trigger: 'axis',
        backgroundColor: 'rgba(0, 0, 0, 0.85)',
        borderColor: 'rgba(255, 255, 255, 0.08)',
        textStyle: { color: '#d1d5db' },
      },
      xAxis: {
        type: 'category',
        data: data.map((d) => d.time),
        axisLine: { lineStyle: { color: 'rgba(255, 255, 255, 0.08)' } },
        axisLabel: { color: 'var(--color-muted-foreground, #9ca3af)' },
      },
      yAxis: {
        type: 'value',
        axisLine: { lineStyle: { color: 'rgba(255, 255, 255, 0.08)' } },
        axisLabel: { color: 'var(--color-muted-foreground, #9ca3af)' },
        splitLine: { lineStyle: { color: 'rgba(255, 255, 255, 0.04)' } },
      },
      series: [
        {
          type: 'line',
          data: data.map((d) => d.value),
          smooth: true,
          showSymbol: false,
          lineStyle: { color: '#3b82f6', width: 2 },
          areaStyle: {
            color: {
              type: 'linear',
              x: 0,
              y: 0,
              x2: 0,
              y2: 1,
              colorStops: [
                { offset: 0, color: 'rgba(59, 130, 246, 0.25)' },
                { offset: 1, color: 'rgba(59, 130, 246, 0.02)' },
              ],
            },
          },
        },
      ],
      grid: { left: 50, right: 20, top: title ? 40 : 10, bottom: 30 },
    }),
    [data, title],
  )

  return <ReactECharts option={option} style={{ height }} />
}
