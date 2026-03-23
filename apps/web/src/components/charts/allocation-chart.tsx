import { useMemo } from 'react'
import ReactECharts from 'echarts-for-react'
import type { EChartsOption } from 'echarts'

interface AllocationItem {
  name: string
  value: number
}

interface AllocationChartProps {
  data: AllocationItem[]
  height?: number
}

const COLORS = ['#3b82f6', '#8b5cf6', '#f59e0b', '#10b981', '#ef4444', '#ec4899']

export function AllocationChart({ data, height = 300 }: AllocationChartProps) {
  const option = useMemo<EChartsOption>(
    () => ({
      backgroundColor: 'transparent',
      tooltip: {
        trigger: 'item',
        backgroundColor: 'rgba(0, 0, 0, 0.85)',
        borderColor: 'rgba(255, 255, 255, 0.08)',
        textStyle: { color: '#d1d5db' },
        formatter: (params: unknown) => {
          const p = params as { name: string; value: number; percent: number }
          return `${p.name}<br/>¥ ${p.value.toLocaleString()}<br/>${p.percent.toFixed(1)}%`
        },
      },
      legend: {
        orient: 'vertical',
        right: 10,
        top: 'center',
        textStyle: { color: 'var(--color-muted-foreground, #9ca3af)' },
      },
      series: [
        {
          type: 'pie',
          radius: ['45%', '70%'],
          center: ['35%', '50%'],
          avoidLabelOverlap: false,
          itemStyle: {
            borderRadius: 6,
            borderColor: 'transparent',
            borderWidth: 2,
          },
          label: {
            show: false,
          },
          emphasis: {
            label: {
              show: true,
              fontSize: 14,
              fontWeight: 'bold',
              color: '#d1d5db',
            },
            itemStyle: {
              shadowBlur: 10,
              shadowColor: 'rgba(0, 0, 0, 0.3)',
            },
          },
          labelLine: { show: false },
          data: data.map((item, i) => ({
            ...item,
            itemStyle: { color: COLORS[i % COLORS.length] },
          })),
        },
      ],
    }),
    [data],
  )

  return <ReactECharts option={option} style={{ height }} />
}
