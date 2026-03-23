import { useMemo } from 'react'
import ReactECharts from 'echarts-for-react'
import type { EChartsOption } from 'echarts'

interface PnlChartProps {
  data: { time: string; value: number }[]
  benchmark?: { time: string; value: number }[]
  title?: string
  height?: number
}

export function PnlChart({ data, benchmark, title, height = 300 }: PnlChartProps) {
  const option = useMemo<EChartsOption>(() => {
    const series: EChartsOption['series'] = [
      {
        name: '策略收益',
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
    ]

    if (benchmark && benchmark.length > 0) {
      series.push({
        name: '基准',
        type: 'line',
        data: benchmark.map((d) => d.value),
        smooth: true,
        showSymbol: false,
        lineStyle: { color: '#a855f7', width: 1.5, type: 'dashed' },
      })
    }

    const showLegend = benchmark && benchmark.length > 0

    return {
      backgroundColor: 'transparent',
      title: title
        ? {
            text: title,
            textStyle: { color: 'var(--color-muted-foreground, #9ca3af)', fontSize: 14 },
            left: 'center',
          }
        : undefined,
      legend: showLegend
        ? {
            show: true,
            top: title ? 25 : 0,
            right: 20,
            textStyle: { color: 'var(--color-muted-foreground, #9ca3af)' },
            data: [
              { name: '策略收益', icon: 'roundRect' },
              { name: '基准', icon: 'roundRect' },
            ],
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
      series,
      grid: {
        left: 50,
        right: 20,
        top: showLegend ? (title ? 55 : 35) : title ? 40 : 10,
        bottom: 30,
      },
    }
  }, [data, benchmark, title])

  return <ReactECharts option={option} style={{ height }} />
}
