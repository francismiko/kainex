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

// --------------- Stochastic ---------------

export interface StochasticResult {
  k: LinePoint[]
  d: LinePoint[]
}

export function calcStochastic(
  data: CandlestickData<Time>[],
  kPeriod = 14,
  dPeriod = 3,
): StochasticResult {
  const k: LinePoint[] = []
  const d: LinePoint[] = []

  if (data.length < kPeriod) return { k, d }

  const kValues: number[] = []

  for (let i = kPeriod - 1; i < data.length; i++) {
    let highest = -Infinity
    let lowest = Infinity
    for (let j = i - kPeriod + 1; j <= i; j++) {
      if (data[j].high > highest) highest = data[j].high
      if (data[j].low < lowest) lowest = data[j].low
    }
    const kVal = highest === lowest ? 50 : ((data[i].close - lowest) / (highest - lowest)) * 100
    kValues.push(kVal)
    k.push({ time: data[i].time, value: kVal })
  }

  // %D = SMA of %K
  if (kValues.length >= dPeriod) {
    let sum = 0
    for (let i = 0; i < dPeriod; i++) sum += kValues[i]
    d.push({ time: k[dPeriod - 1].time, value: sum / dPeriod })
    for (let i = dPeriod; i < kValues.length; i++) {
      sum += kValues[i] - kValues[i - dPeriod]
      d.push({ time: k[i].time, value: sum / dPeriod })
    }
  }

  return { k, d }
}

// --------------- VWAP ---------------

export function calcVWAP(
  data: CandlestickData<Time>[],
  volume?: number[],
): LinePoint[] {
  const result: LinePoint[] = []
  if (data.length === 0) return result

  let cumVolPrice = 0
  let cumVol = 0

  for (let i = 0; i < data.length; i++) {
    const typicalPrice = (data[i].high + data[i].low + data[i].close) / 3
    const vol = volume && volume[i] != null ? volume[i] : generateVolumeFromBar(data[i])
    cumVolPrice += typicalPrice * vol
    cumVol += vol
    if (cumVol > 0) {
      result.push({ time: data[i].time, value: cumVolPrice / cumVol })
    }
  }

  return result
}

function generateVolumeFromBar(bar: CandlestickData<Time>): number {
  const range = bar.high - bar.low
  return Math.round(bar.close * 100 + range * 5000)
}

// --------------- Supertrend ---------------

export interface SupertrendPoint {
  time: Time
  value: number
  color: string
}

export function calcSupertrend(
  data: CandlestickData<Time>[],
  period = 7,
  multiplier = 3.0,
): SupertrendPoint[] {
  const result: SupertrendPoint[] = []
  if (data.length < period + 1) return result

  // Calculate ATR
  const trueRanges: number[] = [data[0].high - data[0].low]
  for (let i = 1; i < data.length; i++) {
    const tr = Math.max(
      data[i].high - data[i].low,
      Math.abs(data[i].high - data[i - 1].close),
      Math.abs(data[i].low - data[i - 1].close),
    )
    trueRanges.push(tr)
  }

  // ATR via SMA for initial, then Wilder's smoothing
  const atr: number[] = new Array(data.length).fill(0)
  let atrSum = 0
  for (let i = 0; i < period; i++) atrSum += trueRanges[i]
  atr[period - 1] = atrSum / period
  for (let i = period; i < data.length; i++) {
    atr[i] = (atr[i - 1] * (period - 1) + trueRanges[i]) / period
  }

  let upperBand = 0
  let lowerBand = 0
  let supertrend = 0
  let prevClose = data[period - 1].close
  let isUpTrend = true

  for (let i = period - 1; i < data.length; i++) {
    const hl2 = (data[i].high + data[i].low) / 2
    const basicUpper = hl2 + multiplier * atr[i]
    const basicLower = hl2 - multiplier * atr[i]

    if (i === period - 1) {
      upperBand = basicUpper
      lowerBand = basicLower
      isUpTrend = data[i].close > hl2
      supertrend = isUpTrend ? lowerBand : upperBand
    } else {
      upperBand = basicUpper < upperBand || prevClose > upperBand ? basicUpper : upperBand
      lowerBand = basicLower > lowerBand || prevClose < lowerBand ? basicLower : lowerBand

      if (isUpTrend) {
        if (data[i].close < lowerBand) {
          isUpTrend = false
          supertrend = upperBand
        } else {
          supertrend = lowerBand
        }
      } else {
        if (data[i].close > upperBand) {
          isUpTrend = true
          supertrend = lowerBand
        } else {
          supertrend = upperBand
        }
      }
    }

    prevClose = data[i].close
    result.push({
      time: data[i].time,
      value: supertrend,
      color: isUpTrend ? '#22c55e' : '#ef4444',
    })
  }

  return result
}

// --------------- Parabolic SAR ---------------

export function calcParabolicSAR(
  data: CandlestickData<Time>[],
  af = 0.02,
  maxAf = 0.2,
): LinePoint[] {
  const result: LinePoint[] = []
  if (data.length < 2) return result

  let isUpTrend = data[1].close > data[0].close
  let sar = isUpTrend ? data[0].low : data[0].high
  let ep = isUpTrend ? data[0].high : data[0].low
  let currentAf = af

  result.push({ time: data[0].time, value: sar })

  for (let i = 1; i < data.length; i++) {
    const prevSar = sar
    sar = prevSar + currentAf * (ep - prevSar)

    if (isUpTrend) {
      // Clamp SAR to be at or below the previous two lows
      if (i >= 2) sar = Math.min(sar, data[i - 1].low, data[i - 2].low)
      else sar = Math.min(sar, data[i - 1].low)

      if (data[i].low < sar) {
        // Reverse to downtrend
        isUpTrend = false
        sar = ep
        ep = data[i].low
        currentAf = af
      } else {
        if (data[i].high > ep) {
          ep = data[i].high
          currentAf = Math.min(currentAf + af, maxAf)
        }
      }
    } else {
      // Clamp SAR to be at or above the previous two highs
      if (i >= 2) sar = Math.max(sar, data[i - 1].high, data[i - 2].high)
      else sar = Math.max(sar, data[i - 1].high)

      if (data[i].high > sar) {
        // Reverse to uptrend
        isUpTrend = true
        sar = ep
        ep = data[i].high
        currentAf = af
      } else {
        if (data[i].low < ep) {
          ep = data[i].low
          currentAf = Math.min(currentAf + af, maxAf)
        }
      }
    }

    result.push({ time: data[i].time, value: sar })
  }

  return result
}

// --------------- Keltner Channel ---------------

export interface KeltnerResult {
  upper: LinePoint[]
  middle: LinePoint[]
  lower: LinePoint[]
}

export function calcKeltner(
  data: CandlestickData<Time>[],
  period = 20,
  multiplier = 1.5,
): KeltnerResult {
  const upper: LinePoint[] = []
  const middle: LinePoint[] = []
  const lower: LinePoint[] = []

  if (data.length < period + 1) return { upper, middle, lower }

  // EMA of close for middle band
  const emaData = calcEMA(data, period)

  // ATR calculation
  const trueRanges: number[] = [data[0].high - data[0].low]
  for (let i = 1; i < data.length; i++) {
    const tr = Math.max(
      data[i].high - data[i].low,
      Math.abs(data[i].high - data[i - 1].close),
      Math.abs(data[i].low - data[i - 1].close),
    )
    trueRanges.push(tr)
  }

  // ATR as EMA of true ranges
  const atrValues = emaValues(trueRanges, period)

  // Both emaData and atrValues start from index (period-1), align them
  const len = Math.min(emaData.length, atrValues.length)
  for (let i = 0; i < len; i++) {
    const mid = emaData[i].value
    const atr = atrValues[i]
    const time = emaData[i].time
    middle.push({ time, value: mid })
    upper.push({ time, value: mid + multiplier * atr })
    lower.push({ time, value: mid - multiplier * atr })
  }

  return { upper, middle, lower }
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
