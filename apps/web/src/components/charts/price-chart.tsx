import { useEffect, useRef } from 'react'
import { createChart, CandlestickSeries, type IChartApi, type ISeriesApi, type CandlestickData, type Time } from 'lightweight-charts'

interface PriceChartProps {
  data: CandlestickData<Time>[]
  /** Optional real-time bar to append/update via series.update() */
  realtimeBar?: CandlestickData<Time> | null
  height?: number
}

function getCSSColor(varName: string, fallback: string): string {
  const value = getComputedStyle(document.documentElement).getPropertyValue(varName).trim()
  return value || fallback
}

export function PriceChart({ data, realtimeBar, height = 400 }: PriceChartProps) {
  const containerRef = useRef<HTMLDivElement>(null)
  const chartRef = useRef<IChartApi | null>(null)
  const seriesRef = useRef<ISeriesApi<'Candlestick'> | null>(null)

  // Create chart once
  useEffect(() => {
    if (!containerRef.current) return

    const profitColor = getCSSColor('--color-profit', '#22c55e')
    const lossColor = getCSSColor('--color-loss', '#ef4444')

    const chart = createChart(containerRef.current, {
      height,
      width: containerRef.current.clientWidth,
      layout: {
        background: { color: 'transparent' },
        textColor: getCSSColor('--color-muted-foreground', '#9ca3af'),
      },
      grid: {
        vertLines: { color: 'rgba(255, 255, 255, 0.04)' },
        horzLines: { color: 'rgba(255, 255, 255, 0.04)' },
      },
      crosshair: {
        mode: 0,
      },
      rightPriceScale: {
        borderColor: 'rgba(255, 255, 255, 0.08)',
      },
      timeScale: {
        borderColor: 'rgba(255, 255, 255, 0.08)',
      },
    })

    const series = chart.addSeries(CandlestickSeries, {
      upColor: profitColor,
      downColor: lossColor,
      borderDownColor: lossColor,
      borderUpColor: profitColor,
      wickDownColor: lossColor,
      wickUpColor: profitColor,
    })

    chartRef.current = chart
    seriesRef.current = series

    // ResizeObserver for container-aware resizing (handles sidebar collapse etc.)
    const ro = new ResizeObserver((entries) => {
      for (const entry of entries) {
        const { width } = entry.contentRect
        if (width > 0) {
          chart.applyOptions({ width })
        }
      }
    })
    ro.observe(containerRef.current)

    return () => {
      ro.disconnect()
      chart.remove()
      chartRef.current = null
      seriesRef.current = null
    }
  }, [height])

  // Update data incrementally without recreating the chart
  useEffect(() => {
    if (!seriesRef.current) return
    seriesRef.current.setData(data)
    chartRef.current?.timeScale().fitContent()
  }, [data])

  // Real-time bar update (append or update the last bar)
  useEffect(() => {
    if (!seriesRef.current || !realtimeBar) return
    seriesRef.current.update(realtimeBar)
  }, [realtimeBar])

  return <div ref={containerRef} />
}
