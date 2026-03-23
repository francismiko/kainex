import { useMemo } from 'react'
import ReactECharts from 'echarts-for-react'
import type { EChartsOption } from 'echarts'

interface MonthlyHeatmapProps {
  equityCurve: { time: string; value: number }[]
  height?: number
}

function computeMonthlyReturns(curve: { time: string; value: number }[]) {
  if (curve.length === 0) return { data: [], years: [], months: [] }

  const monthly = new Map<string, { first: number; last: number }>()
  for (const point of curve) {
    const date = new Date(point.time)
    const key = `${date.getFullYear()}-${date.getMonth() + 1}`
    const entry = monthly.get(key)
    if (!entry) {
      monthly.set(key, { first: point.value, last: point.value })
    } else {
      entry.last = point.value
    }
  }

  const yearsSet = new Set<number>()
  const data: [number, number, number][] = [] // [monthIndex, yearIndex, return%]

  for (const key of monthly.keys()) {
    yearsSet.add(Number(key.split('-')[0]))
  }

  const years = Array.from(yearsSet).sort((a, b) => a - b)
  const months = Array.from({ length: 12 }, (_, i) => `${i + 1}月`)

  for (const [key, { first, last }] of monthly) {
    const [yearStr, monthStr] = key.split('-')
    const yearIdx = years.indexOf(Number(yearStr))
    const monthIdx = Number(monthStr) - 1
    const ret = first !== 0 ? ((last - first) / first) * 100 : 0
    data.push([monthIdx, yearIdx, Math.round(ret * 100) / 100])
  }

  return { data, years: years.map(String), months }
}

export function MonthlyHeatmap({ equityCurve, height = 200 }: MonthlyHeatmapProps) {
  const option = useMemo<EChartsOption>(() => {
    const { data, years, months } = computeMonthlyReturns(equityCurve)

    if (data.length === 0) {
      return { title: { text: '暂无数据', left: 'center', top: 'center', textStyle: { color: '#9ca3af', fontSize: 14 } } }
    }

    const values = data.map((d) => d[2])
    const maxAbs = Math.max(Math.abs(Math.min(...values)), Math.abs(Math.max(...values)), 1)

    return {
      backgroundColor: 'transparent',
      tooltip: {
        formatter: (params: unknown) => {
          const p = params as { value: [number, number, number] }
          return `${years[p.value[1]]}年${months[p.value[0]]}<br/>收益: ${p.value[2].toFixed(2)}%`
        },
      },
      xAxis: {
        type: 'category',
        data: months,
        axisLine: { lineStyle: { color: 'rgba(255, 255, 255, 0.08)' } },
        axisLabel: { color: 'var(--color-muted-foreground, #9ca3af)', fontSize: 11 },
        splitArea: { show: true, areaStyle: { color: ['rgba(255,255,255,0.02)', 'rgba(255,255,255,0.01)'] } },
      },
      yAxis: {
        type: 'category',
        data: years,
        axisLine: { lineStyle: { color: 'rgba(255, 255, 255, 0.08)' } },
        axisLabel: { color: 'var(--color-muted-foreground, #9ca3af)', fontSize: 11 },
      },
      visualMap: {
        min: -maxAbs,
        max: maxAbs,
        calculable: false,
        orient: 'horizontal',
        left: 'center',
        bottom: 0,
        inRange: {
          color: ['#ef4444', '#fca5a5', '#fef2f2', '#f0fdf4', '#86efac', '#22c55e'],
        },
        textStyle: { color: 'var(--color-muted-foreground, #9ca3af)' },
        text: [`${maxAbs.toFixed(1)}%`, `-${maxAbs.toFixed(1)}%`],
      },
      series: [
        {
          type: 'heatmap',
          data,
          label: {
            show: true,
            color: 'var(--color-foreground, #e5e7eb)',
            fontSize: 10,
            formatter: (params: unknown) => {
              const p = params as { value: [number, number, number] }
              return `${p.value[2].toFixed(1)}%`
            },
          },
          emphasis: {
            itemStyle: { shadowBlur: 6, shadowColor: 'rgba(0, 0, 0, 0.3)' },
          },
        },
      ],
      grid: { left: 50, right: 20, top: 10, bottom: 50 },
    }
  }, [equityCurve])

  return <ReactECharts option={option} style={{ height }} />
}
