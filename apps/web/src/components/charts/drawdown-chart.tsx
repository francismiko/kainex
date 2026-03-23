import { useMemo } from 'react'
import ReactECharts from 'echarts-for-react'
import type { EChartsOption } from 'echarts'

interface DrawdownChartProps {
  equityCurve: { time: string; value: number }[]
  height?: number
}

export function DrawdownChart({ equityCurve, height = 200 }: DrawdownChartProps) {
  const option = useMemo<EChartsOption>(() => {
    let peak = -Infinity
    const drawdownData = equityCurve.map((point) => {
      if (point.value > peak) peak = point.value
      const drawdown = peak > 0 ? ((point.value - peak) / peak) * 100 : 0
      return { time: point.time, value: drawdown }
    })

    return {
      backgroundColor: 'transparent',
      tooltip: {
        trigger: 'axis',
        backgroundColor: 'rgba(0, 0, 0, 0.85)',
        borderColor: 'rgba(255, 255, 255, 0.08)',
        textStyle: { color: '#d1d5db' },
        formatter: (params: unknown) => {
          const p = (params as { value: number; axisValue: string }[])[0]
          return `${p.axisValue}<br/>回撤: ${p.value.toFixed(2)}%`
        },
      },
      xAxis: {
        type: 'category',
        data: drawdownData.map((d) => d.time),
        axisLine: { lineStyle: { color: 'rgba(255, 255, 255, 0.08)' } },
        axisLabel: { color: 'var(--color-muted-foreground, #9ca3af)' },
      },
      yAxis: {
        type: 'value',
        max: 0,
        axisLine: { lineStyle: { color: 'rgba(255, 255, 255, 0.08)' } },
        axisLabel: {
          color: 'var(--color-muted-foreground, #9ca3af)',
          formatter: '{value}%',
        },
        splitLine: { lineStyle: { color: 'rgba(255, 255, 255, 0.04)' } },
      },
      series: [
        {
          type: 'line',
          data: drawdownData.map((d) => d.value),
          smooth: true,
          showSymbol: false,
          lineStyle: { color: 'var(--color-loss, #ef4444)', width: 1.5 },
          areaStyle: {
            color: {
              type: 'linear',
              x: 0,
              y: 0,
              x2: 0,
              y2: 1,
              colorStops: [
                { offset: 0, color: 'rgba(239, 68, 68, 0.05)' },
                { offset: 1, color: 'rgba(239, 68, 68, 0.3)' },
              ],
            },
          },
        },
      ],
      grid: { left: 55, right: 20, top: 10, bottom: 30 },
    }
  }, [equityCurve])

  return <ReactECharts option={option} style={{ height }} />
}
