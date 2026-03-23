import { useMemo } from 'react'
import { ScrollArea } from '@/components/ui/scroll-area'
import { cn } from '@/lib/utils'

export interface WatchlistSymbol {
  value: string
  label: string
  market: string
}

interface WatchlistProps {
  symbols: WatchlistSymbol[]
  selected: string
  onSelect: (symbol: string) => void
}

// Generate deterministic mock price/change from symbol name
function mockPrice(symbol: string): { price: number; change: number } {
  let seed = 0
  for (const c of symbol) seed = ((seed << 5) - seed + c.charCodeAt(0)) | 0
  const random = () => {
    seed = (seed * 16807 + 0) % 2147483647
    return (seed & 0x7fffffff) / 0x7fffffff
  }

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

  const price = basePrice * (1 + (random() - 0.5) * 0.02)
  const change = (random() - 0.45) * 6 // slightly bullish bias

  return { price: +price.toFixed(2), change: +change.toFixed(2) }
}

export function Watchlist({ symbols, selected, onSelect }: WatchlistProps) {
  const items = useMemo(
    () =>
      symbols.map((s) => ({
        ...s,
        ...mockPrice(s.value),
      })),
    [symbols],
  )

  return (
    <div className="flex h-full flex-col">
      <div className="flex items-center justify-between border-b px-3 py-2">
        <span className="text-sm font-medium">自选列表</span>
        <span className="text-[10px] text-muted-foreground">
          {symbols.length} 个标的
        </span>
      </div>
      <ScrollArea className="flex-1">
        <div className="py-1">
          {items.map((item) => (
            <button
              key={item.value}
              onClick={() => onSelect(item.value)}
              className={cn(
                'flex w-full items-center justify-between px-3 py-2 text-left transition-colors hover:bg-accent/50',
                selected === item.value && 'bg-accent',
              )}
            >
              <div className="min-w-0 flex-1">
                <div className="truncate text-sm font-medium">
                  {item.label}
                </div>
                <div className="text-[10px] text-muted-foreground">
                  {item.market}
                </div>
              </div>
              <div className="ml-2 text-right">
                <div className="text-sm font-mono tabular-nums">
                  {item.price.toLocaleString('zh-CN', {
                    minimumFractionDigits: 2,
                  })}
                </div>
                <div
                  className={cn(
                    'text-[10px] font-mono tabular-nums',
                    item.change > 0
                      ? 'text-profit'
                      : item.change < 0
                        ? 'text-loss'
                        : 'text-muted-foreground',
                  )}
                >
                  {item.change > 0 ? '+' : ''}
                  {item.change.toFixed(2)}%
                </div>
              </div>
            </button>
          ))}
        </div>
      </ScrollArea>
    </div>
  )
}
