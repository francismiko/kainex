import { useState, useMemo } from 'react'
import { createFileRoute } from '@tanstack/react-router'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Tabs, TabsList, TabsTrigger } from '@/components/ui/tabs'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { PriceChart } from '@/components/charts/price-chart'
import { useMarketBars } from '@/hooks/use-api'
import type { CandlestickData, Time } from 'lightweight-charts'

export const Route = createFileRoute('/market/')({
  component: Market,
})

const symbols = [
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
type Timeframe = typeof timeframes[number]

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
  const basePrice = symbol.includes('BTC') ? 62000 : symbol.includes('ETH') ? 3400 : symbol.includes('SOL') ? 145 : symbol.includes('茅台') ? 1700 : symbol.includes('宁德') ? 220 : symbol.includes('NVDA') ? 860 : symbol.includes('TSLA') ? 245 : 185
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

    const timeStr = tf === '1d'
      ? date.toISOString().split('T')[0]
      : Math.floor(date.getTime() / 1000)

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

function apiBarsToCandles(bars: { open: number; high: number; low: number; close: number; timestamp: string }[]): CandlestickData<Time>[] {
  return bars.map((b) => ({
    time: b.timestamp.split('T')[0] as Time,
    open: b.open,
    high: b.high,
    low: b.low,
    close: b.close,
  }))
}

function Market() {
  const [symbol, setSymbol] = useState('BTC/USDT')
  const [timeframe, setTimeframe] = useState<Timeframe>('1d')

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

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold">行情中心</h1>

      <Card>
        <CardHeader>
          <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
            <div className="flex items-center gap-3">
              <Select value={symbol} onValueChange={setSymbol}>
                <SelectTrigger className="w-[200px]">
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
              <CardTitle className="text-lg">
                {selectedSymbol?.label ?? symbol}
              </CardTitle>
            </div>

            <Tabs value={timeframe} onValueChange={(v: string) => setTimeframe(v as Timeframe)}>
              <TabsList>
                {timeframes.map((tf) => (
                  <TabsTrigger key={tf} value={tf} className="text-xs px-3">
                    {tf}
                  </TabsTrigger>
                ))}
              </TabsList>
            </Tabs>
          </div>
        </CardHeader>
        <CardContent>
          <PriceChart data={candleData} height={500} />
        </CardContent>
      </Card>
    </div>
  )
}
