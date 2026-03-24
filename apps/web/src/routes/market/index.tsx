import { useState, useMemo, useCallback } from 'react'
import { createFileRoute } from '@tanstack/react-router'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Tabs, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { Button } from '@/components/ui/button'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import {
  DropdownMenu,
  DropdownMenuTrigger,
  DropdownMenuContent,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuCheckboxItem,
  DropdownMenuSub,
  DropdownMenuSubTrigger,
  DropdownMenuSubContent,
} from '@/components/ui/dropdown-menu'
import { PriceChart, type IndicatorConfig } from '@/components/charts/price-chart'
import { Watchlist, type WatchlistSymbol } from '@/components/trading/watchlist'
import { useMarketBars } from '@/hooks/use-api'
import { useMarketStream, barToCandlestick } from '@/hooks/use-websocket'
import type { CandlestickData, Time } from 'lightweight-charts'
import { useChartHeight } from '@/hooks/use-mobile'

export const Route = createFileRoute('/market/')({
  component: Market,
})

const symbols: (WatchlistSymbol & { apiMarket: string })[] = [
  { value: 'BTC/USDT', label: 'BTC/USDT', market: '加密货币', apiMarket: 'crypto' },
  { value: 'ETH/USDT', label: 'ETH/USDT', market: '加密货币', apiMarket: 'crypto' },
  { value: 'SOL/USDT', label: 'SOL/USDT', market: '加密货币', apiMarket: 'crypto' },
  { value: '贵州茅台', label: '贵州茅台 (600519)', market: 'A股', apiMarket: 'a_stock' },
  { value: '宁德时代', label: '宁德时代 (300750)', market: 'A股', apiMarket: 'a_stock' },
  { value: 'AAPL', label: 'AAPL', market: '美股', apiMarket: 'us_stock' },
  { value: 'TSLA', label: 'TSLA', market: '美股', apiMarket: 'us_stock' },
  { value: 'NVDA', label: 'NVDA', market: '美股', apiMarket: 'us_stock' },
]

const timeframes = ['1m', '5m', '15m', '1h', '4h', '1d'] as const
type Timeframe = (typeof timeframes)[number]

const timeframeBarCounts: Record<Timeframe, number> = {
  '1m': 240,
  '5m': 200,
  '15m': 160,
  '1h': 120,
  '4h': 100,
  '1d': 100,
}

function generateCandles(symbol: string, tf: Timeframe): CandlestickData<Time>[] {
  let seed = 0
  for (const c of symbol + tf) seed = ((seed << 5) - seed + c.charCodeAt(0)) | 0
  const random = () => {
    seed = (seed * 16807 + 0) % 2147483647
    return (seed & 0x7fffffff) / 0x7fffffff
  }

  const count = timeframeBarCounts[tf]
  const basePrice = symbol.includes('BTC')
    ? 62000
    : symbol.includes('ETH')
      ? 3400
      : symbol.includes('SOL')
        ? 145
        : symbol.includes('茅台')
          ? 1700
          : symbol.includes('宁德')
            ? 220
            : symbol.includes('NVDA')
              ? 860
              : symbol.includes('TSLA')
                ? 245
                : 185
  const volatility = basePrice * 0.008

  const candles: CandlestickData<Time>[] = []
  const startDate = new Date(2026, 0, 1)

  for (let i = 0; i < count; i++) {
    const date = new Date(startDate)
    if (tf === '1d') {
      date.setDate(date.getDate() + i)
    } else if (tf === '4h') {
      date.setHours(date.getHours() + i * 4)
    } else if (tf === '1h') {
      date.setHours(date.getHours() + i)
    } else if (tf === '15m') {
      date.setMinutes(date.getMinutes() + i * 15)
    } else if (tf === '5m') {
      date.setMinutes(date.getMinutes() + i * 5)
    } else {
      date.setMinutes(date.getMinutes() + i)
    }

    const drift = (i / count) * volatility * 2
    const base = basePrice + drift + (random() - 0.5) * volatility * 4
    const open = base + (random() - 0.5) * volatility
    const close = base + (random() - 0.5) * volatility
    const high = Math.max(open, close) + random() * volatility * 0.5
    const low = Math.min(open, close) - random() * volatility * 0.5

    const timeStr =
      tf === '1d' ? date.toISOString().split('T')[0] : Math.floor(date.getTime() / 1000)

    candles.push({
      time: timeStr as Time,
      open: +open.toFixed(2),
      high: +high.toFixed(2),
      low: +low.toFixed(2),
      close: +close.toFixed(2),
    })
  }

  return candles
}

function apiBarsToCandles(
  bars: { open: number; high: number; low: number; close: number; timestamp: string }[],
): CandlestickData<Time>[] {
  return bars.map((b) => ({
    time: b.timestamp.split('T')[0] as Time,
    open: b.open,
    high: b.high,
    low: b.low,
    close: b.close,
  }))
}

// --------------- SMA/EMA period presets ---------------

const PERIOD_OPTIONS = [5, 10, 20, 60] as const

// --------------- Component ---------------

function Market() {
  const chartHeight = useChartHeight(500, 300)
  const [symbol, setSymbol] = useState('BTC/USDT')
  const [timeframe, setTimeframe] = useState<Timeframe>('1d')

  // Indicator state — default: Volume + SMA(20)
  const [volumeEnabled, setVolumeEnabled] = useState(true)
  const [smaPeriods, setSmaPeriods] = useState<number[]>([20])
  const [emaPeriods, setEmaPeriods] = useState<number[]>([])
  const [bollingerEnabled, setBollingerEnabled] = useState(false)
  const [rsiEnabled, setRsiEnabled] = useState(false)
  const [macdEnabled, setMacdEnabled] = useState(false)
  const [stochasticEnabled, setStochasticEnabled] = useState(false)
  const [supertrendEnabled, setSupertrendEnabled] = useState(false)
  const [parabolicSarEnabled, setParabolicSarEnabled] = useState(false)
  const [keltnerEnabled, setKeltnerEnabled] = useState(false)

  const selectedSymbol = symbols.find((s) => s.value === symbol)

  const barsQuery = useMarketBars({
    symbol,
    market: selectedSymbol?.apiMarket ?? 'crypto',
    timeframe,
    limit: timeframeBarCounts[timeframe],
  })

  const candleData = useMemo(() => {
    if (barsQuery.data && barsQuery.data.length > 0) {
      return apiBarsToCandles(barsQuery.data)
    }
    return generateCandles(symbol, timeframe)
  }, [barsQuery.data, symbol, timeframe])

  const { latestBar, status: wsStatus } = useMarketStream(symbol, timeframe)

  const realtimeCandle = useMemo<CandlestickData<Time> | null>(() => {
    if (!latestBar) return null
    const converted = barToCandlestick(latestBar)
    return {
      ...converted,
      time: converted.time as Time,
    }
  }, [latestBar])

  // Build indicator config
  const indicators = useMemo<IndicatorConfig>(() => {
    const config: IndicatorConfig = {}
    if (smaPeriods.length > 0) config.sma = smaPeriods
    if (emaPeriods.length > 0) config.ema = emaPeriods
    if (bollingerEnabled) config.bollinger = { period: 20, stdDev: 2 }
    if (volumeEnabled) config.volume = true
    if (rsiEnabled) config.rsi = 14
    if (macdEnabled) config.macd = { fast: 12, slow: 26, signal: 9 }
    if (stochasticEnabled) config.stochastic = { kPeriod: 14, dPeriod: 3 }
    if (supertrendEnabled) config.supertrend = { period: 7, multiplier: 3.0 }
    if (parabolicSarEnabled) config.parabolicSar = { af: 0.02, maxAf: 0.2 }
    if (keltnerEnabled) config.keltner = { period: 20, multiplier: 1.5 }
    return config
  }, [smaPeriods, emaPeriods, bollingerEnabled, volumeEnabled, rsiEnabled, macdEnabled, stochasticEnabled, supertrendEnabled, parabolicSarEnabled, keltnerEnabled])

  const toggleSmaPeriod = useCallback((period: number) => {
    setSmaPeriods((prev) =>
      prev.includes(period) ? prev.filter((p) => p !== period) : [...prev, period],
    )
  }, [])

  const toggleEmaPeriod = useCallback((period: number) => {
    setEmaPeriods((prev) =>
      prev.includes(period) ? prev.filter((p) => p !== period) : [...prev, period],
    )
  }, [])

  // Count active indicators for the badge
  const activeCount =
    smaPeriods.length +
    emaPeriods.length +
    (bollingerEnabled ? 1 : 0) +
    (volumeEnabled ? 1 : 0) +
    (rsiEnabled ? 1 : 0) +
    (macdEnabled ? 1 : 0) +
    (stochasticEnabled ? 1 : 0) +
    (supertrendEnabled ? 1 : 0) +
    (parabolicSarEnabled ? 1 : 0) +
    (keltnerEnabled ? 1 : 0)

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold">行情中心</h1>
        <div className="flex items-center gap-2 text-xs text-muted-foreground">
          <span
            className={`inline-block h-2 w-2 rounded-full ${
              wsStatus === 'connected'
                ? 'bg-green-500'
                : wsStatus === 'connecting'
                  ? 'bg-yellow-500 animate-pulse'
                  : 'bg-gray-400'
            }`}
          />
          <span>
            {wsStatus === 'connected'
              ? '实时连接'
              : wsStatus === 'connecting'
                ? '连接中...'
                : '离线'}
          </span>
        </div>
      </div>

      <div className="flex gap-4">
        {/* Watchlist sidebar */}
        <Card className="hidden w-56 shrink-0 lg:block">
          <Watchlist
            symbols={symbols}
            selected={symbol}
            onSelect={setSymbol}
          />
        </Card>

        {/* Main chart area */}
        <Card className="min-w-0 flex-1">
          <CardHeader>
            <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
              <div className="flex items-center gap-3">
                <Select value={symbol} onValueChange={setSymbol}>
                  <SelectTrigger className="w-[200px] lg:hidden">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    {symbols.map((s) => (
                      <SelectItem key={s.value} value={s.value}>
                        <span>{s.label}</span>
                        <span className="ml-2 text-xs text-muted-foreground">{s.market}</span>
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
                <CardTitle className="text-lg">{selectedSymbol?.label ?? symbol}</CardTitle>
                {latestBar && (
                  <span className="text-sm font-mono text-muted-foreground">
                    {latestBar.close.toFixed(2)}
                  </span>
                )}
              </div>

              <div className="flex items-center gap-2">
                {/* Indicator dropdown */}
                <DropdownMenu>
                  <DropdownMenuTrigger asChild>
                    <Button variant="outline" size="sm">
                      指标
                      {activeCount > 0 && (
                        <span className="ml-1 rounded-full bg-primary px-1.5 py-0.5 text-[10px] text-primary-foreground">
                          {activeCount}
                        </span>
                      )}
                    </Button>
                  </DropdownMenuTrigger>
                  <DropdownMenuContent align="end" className="w-52">
                    {/* Overlay indicators */}
                    <DropdownMenuLabel>主图叠加</DropdownMenuLabel>
                    <DropdownMenuSub>
                      <DropdownMenuSubTrigger>
                        SMA
                        {smaPeriods.length > 0 && (
                          <span className="ml-auto text-[10px] text-muted-foreground">
                            {smaPeriods.join(',')}
                          </span>
                        )}
                      </DropdownMenuSubTrigger>
                      <DropdownMenuSubContent>
                        {PERIOD_OPTIONS.map((p) => (
                          <DropdownMenuCheckboxItem
                            key={`sma-${p}`}
                            checked={smaPeriods.includes(p)}
                            onCheckedChange={() => toggleSmaPeriod(p)}
                            onSelect={(e) => e.preventDefault()}
                          >
                            SMA({p})
                          </DropdownMenuCheckboxItem>
                        ))}
                      </DropdownMenuSubContent>
                    </DropdownMenuSub>
                    <DropdownMenuSub>
                      <DropdownMenuSubTrigger>
                        EMA
                        {emaPeriods.length > 0 && (
                          <span className="ml-auto text-[10px] text-muted-foreground">
                            {emaPeriods.join(',')}
                          </span>
                        )}
                      </DropdownMenuSubTrigger>
                      <DropdownMenuSubContent>
                        {PERIOD_OPTIONS.map((p) => (
                          <DropdownMenuCheckboxItem
                            key={`ema-${p}`}
                            checked={emaPeriods.includes(p)}
                            onCheckedChange={() => toggleEmaPeriod(p)}
                            onSelect={(e) => e.preventDefault()}
                          >
                            EMA({p})
                          </DropdownMenuCheckboxItem>
                        ))}
                      </DropdownMenuSubContent>
                    </DropdownMenuSub>
                    <DropdownMenuCheckboxItem
                      checked={bollingerEnabled}
                      onCheckedChange={(v) => setBollingerEnabled(!!v)}
                      onSelect={(e) => e.preventDefault()}
                    >
                      Bollinger Bands (20, 2)
                    </DropdownMenuCheckboxItem>
                    <DropdownMenuCheckboxItem
                      checked={keltnerEnabled}
                      onCheckedChange={(v) => setKeltnerEnabled(!!v)}
                      onSelect={(e) => e.preventDefault()}
                    >
                      Keltner Channel (20, 1.5)
                    </DropdownMenuCheckboxItem>
                    <DropdownMenuCheckboxItem
                      checked={supertrendEnabled}
                      onCheckedChange={(v) => setSupertrendEnabled(!!v)}
                      onSelect={(e) => e.preventDefault()}
                    >
                      Supertrend (7, 3)
                    </DropdownMenuCheckboxItem>
                    <DropdownMenuCheckboxItem
                      checked={parabolicSarEnabled}
                      onCheckedChange={(v) => setParabolicSarEnabled(!!v)}
                      onSelect={(e) => e.preventDefault()}
                    >
                      Parabolic SAR
                    </DropdownMenuCheckboxItem>

                    <DropdownMenuSeparator />

                    {/* Sub-chart indicators */}
                    <DropdownMenuLabel>副图指标</DropdownMenuLabel>
                    <DropdownMenuCheckboxItem
                      checked={volumeEnabled}
                      onCheckedChange={(v) => setVolumeEnabled(!!v)}
                      onSelect={(e) => e.preventDefault()}
                    >
                      成交量 (VOL)
                    </DropdownMenuCheckboxItem>
                    <DropdownMenuCheckboxItem
                      checked={rsiEnabled}
                      onCheckedChange={(v) => setRsiEnabled(!!v)}
                      onSelect={(e) => e.preventDefault()}
                    >
                      RSI (14)
                    </DropdownMenuCheckboxItem>
                    <DropdownMenuCheckboxItem
                      checked={macdEnabled}
                      onCheckedChange={(v) => setMacdEnabled(!!v)}
                      onSelect={(e) => e.preventDefault()}
                    >
                      MACD (12, 26, 9)
                    </DropdownMenuCheckboxItem>
                    <DropdownMenuCheckboxItem
                      checked={stochasticEnabled}
                      onCheckedChange={(v) => setStochasticEnabled(!!v)}
                      onSelect={(e) => e.preventDefault()}
                    >
                      Stochastic (14, 3)
                    </DropdownMenuCheckboxItem>
                  </DropdownMenuContent>
                </DropdownMenu>

                <Tabs
                  value={timeframe}
                  onValueChange={(v: string) => setTimeframe(v as Timeframe)}
                >
                  <TabsList>
                    {timeframes.map((tf) => (
                      <TabsTrigger key={tf} value={tf} className="text-xs px-3">
                        {tf}
                      </TabsTrigger>
                    ))}
                  </TabsList>
                </Tabs>
              </div>
            </div>
          </CardHeader>
          <CardContent>
            <PriceChart
              data={candleData}
              realtimeBar={realtimeCandle}
              height={chartHeight}
              indicators={indicators}
            />
          </CardContent>
        </Card>
      </div>
    </div>
  )
}
