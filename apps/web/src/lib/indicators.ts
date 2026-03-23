import type { CandlestickData, Time } from 'lightweight-charts'

// --------------- Types ---------------

export interface LinePoint {
  time: Time
  value: number
}

export interface HistogramPoint {
  time: Time
  value: number
  color?: string
}

export interface VolumePoint {
  time: Time
  value: number
  color: string
}

export interface BollingerResult {
  upper: LinePoint[]
  middle: LinePoint[]
  lower: LinePoint[]
}

export interface MACDResult {
  macd: LinePoint[]
  signal: LinePoint[]
  histogram: HistogramPoint[]
}

// --------------- SMA ---------------

export function calcSMA(
  data: CandlestickData<Time>[],
  period: number,
): LinePoint[] {
  const result: LinePoint[] = []
  if (data.length < period) return result

  let sum = 0
  for (let i = 0; i < period; i++) {
    sum += data[i].close
  }
  result.push({ time: data[period - 1].time, value: sum / period })

  for (let i = period; i < data.length; i++) {
    sum += data[i].close - data[i - period].close
    result.push({ time: data[i].time, value: sum / period })
  }

  return result
}

// --------------- EMA ---------------

export function calcEMA(
  data: CandlestickData<Time>[],
  period: number,
): LinePoint[] {
  const result: LinePoint[] = []
  if (data.length < period) return result

  const k = 2 / (period + 1)

  // Seed with SMA of first `period` bars
  let sum = 0
  for (let i = 0; i < period; i++) {
    sum += data[i].close
  }
  let ema = sum / period
  result.push({ time: data[period - 1].time, value: ema })

  for (let i = period; i < data.length; i++) {
    ema = data[i].close * k + ema * (1 - k)
    result.push({ time: data[i].time, value: ema })
  }

  return result
}

// --------------- Bollinger Bands ---------------

export function calcBollinger(
  data: CandlestickData<Time>[],
  period: number,
  stdDev: number,
): BollingerResult {
  const upper: LinePoint[] = []
  const middle: LinePoint[] = []
  const lower: LinePoint[] = []

  if (data.length < period) return { upper, middle, lower }

  for (let i = period - 1; i < data.length; i++) {
    let sum = 0
    for (let j = i - period + 1; j <= i; j++) {
      sum += data[j].close
    }
    const mean = sum / period

    let sqSum = 0
    for (let j = i - period + 1; j <= i; j++) {
      const diff = data[j].close - mean
      sqSum += diff * diff
    }
    const std = Math.sqrt(sqSum / period)

    middle.push({ time: data[i].time, value: mean })
    upper.push({ time: data[i].time, value: mean + stdDev * std })
    lower.push({ time: data[i].time, value: mean - stdDev * std })
  }

  return { upper, middle, lower }
}

// --------------- Volume ---------------

export function calcVolume(
  data: CandlestickData<Time>[],
  profitColor: string,
  lossColor: string,
): VolumePoint[] {
  return data.map((bar) => ({
    time: bar.time,
    value: generateVolume(bar),
    color: bar.close >= bar.open ? profitColor : lossColor,
  }))
}

/**
 * Generate a deterministic pseudo-volume from bar data.
 * Real volume would come from the API; this is a fallback for mock data.
 */
function generateVolume(bar: CandlestickData<Time>): number {
  const range = bar.high - bar.low
  const base = bar.close * 100
  // Use price range as a proxy for activity
  return Math.round(base + range * 5000)
}

// --------------- RSI ---------------

export function calcRSI(
  data: CandlestickData<Time>[],
  period: number,
): LinePoint[] {
  const result: LinePoint[] = []
  if (data.length < period + 1) return result

  let avgGain = 0
  let avgLoss = 0

  // First period: simple average
  for (let i = 1; i <= period; i++) {
    const change = data[i].close - data[i - 1].close
    if (change > 0) avgGain += change
    else avgLoss += Math.abs(change)
  }
  avgGain /= period
  avgLoss /= period

  const rs = avgLoss === 0 ? 100 : avgGain / avgLoss
  result.push({
    time: data[period].time,
    value: 100 - 100 / (1 + rs),
  })

  // Subsequent periods: smoothed (Wilder's) average
  for (let i = period + 1; i < data.length; i++) {
    const change = data[i].close - data[i - 1].close
    const gain = change > 0 ? change : 0
    const loss = change < 0 ? Math.abs(change) : 0

    avgGain = (avgGain * (period - 1) + gain) / period
    avgLoss = (avgLoss * (period - 1) + loss) / period

    const rsi = avgLoss === 0 ? 100 : 100 - 100 / (1 + avgGain / avgLoss)
    result.push({ time: data[i].time, value: rsi })
  }

  return result
}

// --------------- MACD ---------------

export function calcMACD(
  data: CandlestickData<Time>[],
  fast: number,
  slow: number,
  signal: number,
): MACDResult {
  const macdLine: LinePoint[] = []
  const signalLine: LinePoint[] = []
  const histogram: HistogramPoint[] = []

  if (data.length < slow) return { macd: macdLine, signal: signalLine, histogram }

  // Calculate fast and slow EMA on close prices
  const fastEMA = emaValues(data.map((d) => d.close), fast)
  const slowEMA = emaValues(data.map((d) => d.close), slow)

  // MACD line = fast EMA - slow EMA (aligned from index slow-1)
  const macdValues: number[] = []
  const startIdx = slow - 1 // slowEMA starts producing values here

  for (let i = 0; i < slowEMA.length; i++) {
    const fastIdx = i + (slow - fast) // align fast to slow
    if (fastIdx < 0 || fastIdx >= fastEMA.length) continue
    macdValues.push(fastEMA[fastIdx] - slowEMA[i])
  }

  if (macdValues.length < signal) return { macd: macdLine, signal: signalLine, histogram }

  // Signal line = EMA of MACD values
  const signalEMA = emaValues(macdValues, signal)

  // Align output with time axis
  const macdStartTime = startIdx
  for (let i = 0; i < macdValues.length; i++) {
    const timeIdx = macdStartTime + i
    if (timeIdx >= data.length) break
    macdLine.push({ time: data[timeIdx].time, value: macdValues[i] })
  }

  const signalStartTime = macdStartTime + signal - 1
  for (let i = 0; i < signalEMA.length; i++) {
    const timeIdx = signalStartTime + i
    if (timeIdx >= data.length) break
    const macdVal = macdValues[signal - 1 + i]
    const sigVal = signalEMA[i]
    signalLine.push({ time: data[timeIdx].time, value: sigVal })
    const histVal = macdVal - sigVal
    histogram.push({
      time: data[timeIdx].time,
      value: histVal,
      color: histVal >= 0 ? '#26a69a' : '#ef5350',
    })
  }

  return { macd: macdLine, signal: signalLine, histogram }
}

// --------------- Helper: raw EMA on number array ---------------

function emaValues(values: number[], period: number): number[] {
  const result: number[] = []
  if (values.length < period) return result

  const k = 2 / (period + 1)

  let sum = 0
  for (let i = 0; i < period; i++) {
    sum += values[i]
  }
  let ema = sum / period
  result.push(ema)

  for (let i = period; i < values.length; i++) {
    ema = values[i] * k + ema * (1 - k)
    result.push(ema)
  }

  return result
}
