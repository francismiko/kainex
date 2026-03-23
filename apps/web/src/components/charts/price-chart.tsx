import { useEffect, useRef, useMemo } from 'react'
import {
  createChart,
  CandlestickSeries,
  LineSeries,
  HistogramSeries,
  type IChartApi,
  type ISeriesApi,
  type CandlestickData,
  type Time,
  type LineData,
  type HistogramData,
} from 'lightweight-charts'
import {
  calcSMA,
  calcEMA,
  calcBollinger,
  calcVolume,
  calcRSI,
  calcMACD,
} from '@/lib/indicators'

// --------------- Types ---------------

export interface IndicatorConfig {
  sma?: number[]
  ema?: number[]
  bollinger?: { period: number; stdDev: number }
  volume?: boolean
  rsi?: number
  macd?: { fast: number; slow: number; signal: number }
}

interface PriceChartProps {
  data: CandlestickData<Time>[]
  realtimeBar?: CandlestickData<Time> | null
  height?: number
  indicators?: IndicatorConfig
}

// --------------- Colors ---------------

const SMA_COLORS = ['#f59e0b', '#3b82f6', '#8b5cf6', '#ec4899'] as const
const EMA_COLORS = ['#06b6d4', '#10b981', '#f97316', '#a855f7'] as const
const BB_COLOR = '#6366f1'
const RSI_COLOR = '#e879f9'
const MACD_FAST_COLOR = '#3b82f6'
const MACD_SLOW_COLOR = '#ef4444'

function getCSSColor(varName: string, fallback: string): string {
  const value = getComputedStyle(document.documentElement)
    .getPropertyValue(varName)
    .trim()
  return value || fallback
}

// --------------- Component ---------------

export function PriceChart({
  data,
  realtimeBar,
  height = 400,
  indicators,
}: PriceChartProps) {
  // Calculate how much height goes to sub-panes
  const subPaneCount = [
    indicators?.volume,
    indicators?.rsi,
    indicators?.macd,
  ].filter(Boolean).length

  const mainChartHeight = subPaneCount > 0
    ? height - subPaneCount * 120
    : height

  return (
    <div className="flex flex-col gap-0.5">
      <MainChart
        data={data}
        realtimeBar={realtimeBar}
        height={Math.max(mainChartHeight, 200)}
        indicators={indicators}
      />
      {indicators?.volume && (
        <SubChart
          type="volume"
          data={data}
          indicators={indicators}
          height={120}
        />
      )}
      {indicators?.rsi && (
        <SubChart
          type="rsi"
          data={data}
          indicators={indicators}
          height={120}
        />
      )}
      {indicators?.macd && (
        <SubChart
          type="macd"
          data={data}
          indicators={indicators}
          height={120}
        />
      )}
    </div>
  )
}

// --------------- Main Chart (Candlestick + Overlays) ---------------

function MainChart({
  data,
  realtimeBar,
  height,
  indicators,
}: {
  data: CandlestickData<Time>[]
  realtimeBar?: CandlestickData<Time> | null
  height: number
  indicators?: IndicatorConfig
}) {
  const containerRef = useRef<HTMLDivElement>(null)
  const chartRef = useRef<IChartApi | null>(null)
  const candleSeriesRef = useRef<ISeriesApi<'Candlestick'> | null>(null)
  const overlaySeriesRef = useRef<ISeriesApi<'Line'>[]>([])

  // Compute overlay data
  const overlays = useMemo(() => {
    if (!indicators || data.length === 0) return []

    const result: {
      key: string
      data: LineData<Time>[]
      color: string
      lineWidth: number
      lineStyle?: number
    }[] = []

    // SMA
    if (indicators.sma) {
      indicators.sma.forEach((period, i) => {
        const smaData = calcSMA(data, period)
        result.push({
          key: `sma-${period}`,
          data: smaData.map((p) => ({ time: p.time, value: p.value })),
          color: SMA_COLORS[i % SMA_COLORS.length],
          lineWidth: 1,
        })
      })
    }

    // EMA
    if (indicators.ema) {
      indicators.ema.forEach((period, i) => {
        const emaData = calcEMA(data, period)
        result.push({
          key: `ema-${period}`,
          data: emaData.map((p) => ({ time: p.time, value: p.value })),
          color: EMA_COLORS[i % EMA_COLORS.length],
          lineWidth: 1,
        })
      })
    }

    // Bollinger Bands
    if (indicators.bollinger) {
      const bb = calcBollinger(
        data,
        indicators.bollinger.period,
        indicators.bollinger.stdDev,
      )
      result.push({
        key: 'bb-middle',
        data: bb.middle.map((p) => ({ time: p.time, value: p.value })),
        color: BB_COLOR,
        lineWidth: 1,
      })
      result.push({
        key: 'bb-upper',
        data: bb.upper.map((p) => ({ time: p.time, value: p.value })),
        color: BB_COLOR,
        lineWidth: 1,
        lineStyle: 2, // Dashed
      })
      result.push({
        key: 'bb-lower',
        data: bb.lower.map((p) => ({ time: p.time, value: p.value })),
        color: BB_COLOR,
        lineWidth: 1,
        lineStyle: 2, // Dashed
      })
    }

    return result
  }, [data, indicators])

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
    candleSeriesRef.current = series

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
      candleSeriesRef.current = null
      overlaySeriesRef.current = []
    }
  }, [height])

  // Update candle data + overlays
  useEffect(() => {
    const chart = chartRef.current
    const candleSeries = candleSeriesRef.current
    if (!chart || !candleSeries) return

    candleSeries.setData(data)

    // Remove old overlay series
    for (const s of overlaySeriesRef.current) {
      chart.removeSeries(s)
    }
    overlaySeriesRef.current = []

    // Add new overlay series
    for (const overlay of overlays) {
      const lineSeries = chart.addSeries(LineSeries, {
        color: overlay.color,
        lineWidth: overlay.lineWidth as 1 | 2 | 3 | 4,
        lineStyle: overlay.lineStyle,
        crosshairMarkerVisible: false,
        lastValueVisible: false,
        priceLineVisible: false,
      })
      lineSeries.setData(overlay.data)
      overlaySeriesRef.current.push(lineSeries)
    }

    chart.timeScale().fitContent()
  }, [data, overlays])

  // Real-time bar update
  useEffect(() => {
    if (!candleSeriesRef.current || !realtimeBar) return
    candleSeriesRef.current.update(realtimeBar)
  }, [realtimeBar])

  return <div ref={containerRef} />
}

// --------------- Sub Charts (Volume, RSI, MACD) ---------------

function SubChart({
  type,
  data,
  indicators,
  height,
}: {
  type: 'volume' | 'rsi' | 'macd'
  data: CandlestickData<Time>[]
  indicators: IndicatorConfig
  height: number
}) {
  const containerRef = useRef<HTMLDivElement>(null)
  const chartRef = useRef<IChartApi | null>(null)

  const seriesData = useMemo(() => {
    if (data.length === 0) return null

    const profitColor = getCSSColor('--color-profit', '#22c55e')
    const lossColor = getCSSColor('--color-loss', '#ef4444')

    if (type === 'volume') {
      return {
        type: 'volume' as const,
        histogram: calcVolume(data, profitColor + '80', lossColor + '80'),
      }
    }

    if (type === 'rsi' && indicators.rsi) {
      return {
        type: 'rsi' as const,
        line: calcRSI(data, indicators.rsi),
      }
    }

    if (type === 'macd' && indicators.macd) {
      return {
        type: 'macd' as const,
        ...calcMACD(
          data,
          indicators.macd.fast,
          indicators.macd.slow,
          indicators.macd.signal,
        ),
      }
    }

    return null
  }, [data, type, indicators])

  // Create chart
  useEffect(() => {
    if (!containerRef.current) return

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
        visible: false,
      },
    })

    chartRef.current = chart

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
    }
  }, [height])

  // Update series data
  useEffect(() => {
    const chart = chartRef.current
    if (!chart || !seriesData) return

    // Remove all existing series by recreating them
    // (Lightweight charts v5 doesn't have a "clear all series" method)
    // Instead we track and remove
    const panes = chart.panes()
    const existingSeries: ISeriesApi<
      'Line' | 'Histogram',
      Time
    >[] = []
    for (const pane of panes) {
      const paneSeries = pane.getSeries()
      for (const s of paneSeries) {
        existingSeries.push(
          s as unknown as ISeriesApi<'Line' | 'Histogram', Time>,
        )
      }
    }
    for (const s of existingSeries) {
      try {
        chart.removeSeries(s)
      } catch {
        // Series might already be removed
      }
    }

    if (seriesData.type === 'volume') {
      const volSeries = chart.addSeries(HistogramSeries, {
        priceFormat: { type: 'volume' },
        priceScaleId: 'vol',
        lastValueVisible: false,
        priceLineVisible: false,
      })
      chart.priceScale('vol').applyOptions({
        scaleMargins: { top: 0.1, bottom: 0 },
      })
      volSeries.setData(
        seriesData.histogram.map((p) => ({
          time: p.time,
          value: p.value,
          color: p.color,
        })) as HistogramData<Time>[],
      )
    }

    if (seriesData.type === 'rsi') {
      const rsiSeries = chart.addSeries(LineSeries, {
        color: RSI_COLOR,
        lineWidth: 1,
        lastValueVisible: false,
        priceLineVisible: false,
      })
      rsiSeries.setData(
        seriesData.line.map((p) => ({
          time: p.time,
          value: p.value,
        })) as LineData<Time>[],
      )

      // Overbought/Oversold reference lines via price lines
      rsiSeries.createPriceLine({
        price: 70,
        color: 'rgba(239, 68, 68, 0.4)',
        lineWidth: 1,
        lineStyle: 2,
        axisLabelVisible: true,
        title: '',
      })
      rsiSeries.createPriceLine({
        price: 30,
        color: 'rgba(34, 197, 94, 0.4)',
        lineWidth: 1,
        lineStyle: 2,
        axisLabelVisible: true,
        title: '',
      })

      chart.priceScale('right').applyOptions({
        scaleMargins: { top: 0.05, bottom: 0.05 },
      })
    }

    if (seriesData.type === 'macd') {
      const histSeries = chart.addSeries(HistogramSeries, {
        lastValueVisible: false,
        priceLineVisible: false,
      })
      histSeries.setData(
        seriesData.histogram.map((p) => ({
          time: p.time,
          value: p.value,
          color: p.color,
        })) as HistogramData<Time>[],
      )

      const macdSeries = chart.addSeries(LineSeries, {
        color: MACD_FAST_COLOR,
        lineWidth: 1,
        lastValueVisible: false,
        priceLineVisible: false,
      })
      macdSeries.setData(
        seriesData.macd.map((p) => ({
          time: p.time,
          value: p.value,
        })) as LineData<Time>[],
      )

      const signalSeries = chart.addSeries(LineSeries, {
        color: MACD_SLOW_COLOR,
        lineWidth: 1,
        lastValueVisible: false,
        priceLineVisible: false,
      })
      signalSeries.setData(
        seriesData.signal.map((p) => ({
          time: p.time,
          value: p.value,
        })) as LineData<Time>[],
      )

      // Zero line
      histSeries.createPriceLine({
        price: 0,
        color: 'rgba(255, 255, 255, 0.15)',
        lineWidth: 1,
        lineStyle: 2,
        axisLabelVisible: false,
        title: '',
      })
    }

    chart.timeScale().fitContent()
  }, [seriesData])

  // Label for the sub-chart
  const label =
    type === 'volume'
      ? 'VOL'
      : type === 'rsi'
        ? `RSI(${indicators.rsi})`
        : type === 'macd'
          ? `MACD(${indicators.macd?.fast},${indicators.macd?.slow},${indicators.macd?.signal})`
          : ''

  return (
    <div className="relative">
      <span className="absolute left-2 top-1 z-10 text-[10px] text-muted-foreground">
        {label}
      </span>
      <div ref={containerRef} />
    </div>
  )
}
