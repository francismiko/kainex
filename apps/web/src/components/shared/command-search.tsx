import { useEffect, useState, useCallback } from 'react'
import { useNavigate } from '@tanstack/react-router'
import {
  CommandDialog,
  CommandEmpty,
  CommandGroup,
  CommandInput,
  CommandItem,
  CommandList,
  CommandSeparator,
} from '@/components/ui/command'
import {
  LayoutDashboard,
  Bot,
  GitCompareArrows,
  LineChart,
  ArrowRightLeft,
  Briefcase,
  ShieldAlert,
  Settings,
  Coins,
} from 'lucide-react'

interface SearchItem {
  label: string
  to: string
  icon: typeof LayoutDashboard
  group: 'pages' | 'strategies' | 'pairs'
}

const pageItems: SearchItem[] = [
  { label: '总览', to: '/', icon: LayoutDashboard, group: 'pages' },
  { label: '策略管理', to: '/strategies', icon: Bot, group: 'pages' },
  { label: '策略对比', to: '/strategies/compare', icon: GitCompareArrows, group: 'pages' },
  { label: '行情中心', to: '/market', icon: LineChart, group: 'pages' },
  { label: '交易记录', to: '/trades', icon: ArrowRightLeft, group: 'pages' },
  { label: '持仓组合', to: '/portfolio', icon: Briefcase, group: 'pages' },
  { label: '风控监控', to: '/risk', icon: ShieldAlert, group: 'pages' },
  { label: '设置', to: '/settings', icon: Settings, group: 'pages' },
]

const strategyItems: SearchItem[] = [
  { label: 'SMA 交叉', to: '/strategies', icon: Bot, group: 'strategies' },
  { label: 'RSI 均值回归', to: '/strategies', icon: Bot, group: 'strategies' },
  { label: '布林带突破', to: '/strategies', icon: Bot, group: 'strategies' },
  { label: '动量跟踪', to: '/strategies', icon: Bot, group: 'strategies' },
  { label: '配对交易', to: '/strategies', icon: Bot, group: 'strategies' },
]

const pairItems: SearchItem[] = [
  { label: 'BTC/USDT', to: '/market', icon: Coins, group: 'pairs' },
  { label: 'ETH/USDT', to: '/market', icon: Coins, group: 'pairs' },
  { label: 'AAPL', to: '/market', icon: Coins, group: 'pairs' },
  { label: 'TSLA', to: '/market', icon: Coins, group: 'pairs' },
  { label: '贵州茅台', to: '/market', icon: Coins, group: 'pairs' },
]

const allItems = [...pageItems, ...strategyItems, ...pairItems]

const groupLabels: Record<string, string> = {
  pages: '页面',
  strategies: '策略',
  pairs: '交易对',
}

export function CommandSearch() {
  const [open, setOpen] = useState(false)
  const navigate = useNavigate()

  useEffect(() => {
    function onKeyDown(e: KeyboardEvent) {
      if (e.key === 'k' && (e.metaKey || e.ctrlKey)) {
        e.preventDefault()
        setOpen((prev) => !prev)
      }
    }
    document.addEventListener('keydown', onKeyDown)
    return () => document.removeEventListener('keydown', onKeyDown)
  }, [])

  const handleSelect = useCallback(
    (to: string) => {
      setOpen(false)
      void navigate({ to })
    },
    [navigate],
  )

  const groups = ['pages', 'strategies', 'pairs'] as const

  return (
    <CommandDialog
      open={open}
      onOpenChange={setOpen}
      title="全局搜索"
      description="搜索页面、策略或交易对"
    >
      <CommandInput placeholder="搜索页面、策略、交易对..." />
      <CommandList>
        <CommandEmpty>没有找到匹配结果</CommandEmpty>
        {groups.map((group, idx) => {
          const items = allItems.filter((item) => item.group === group)
          return (
            <div key={group}>
              {idx > 0 && <CommandSeparator />}
              <CommandGroup heading={groupLabels[group]}>
                {items.map((item) => (
                  <CommandItem
                    key={`${item.group}-${item.label}`}
                    value={`${item.label} ${item.to}`}
                    onSelect={() => handleSelect(item.to)}
                  >
                    <item.icon className="h-4 w-4" />
                    <span>{item.label}</span>
                  </CommandItem>
                ))}
              </CommandGroup>
            </div>
          )
        })}
      </CommandList>
    </CommandDialog>
  )
}
