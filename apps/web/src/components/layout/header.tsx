import { Moon, Sun, Search, Wifi, WifiOff } from 'lucide-react'
import { useRouterState, Link } from '@tanstack/react-router'
import { useUIStore } from '@/stores/ui-store'
import { useConnectionStatus } from '@/hooks/use-websocket'
import { Button } from '@/components/ui/button'
import { Separator } from '@/components/ui/separator'
import { Tooltip, TooltipContent, TooltipTrigger } from '@/components/ui/tooltip'

const routeLabels: Record<string, string> = {
  '/': '总览',
  '/strategies': '策略管理',
  '/market': '行情中心',
  '/trades': '交易记录',
  '/portfolio': '持仓组合',
  '/risk': '风控监控',
  '/settings': '设置',
}

export function Header() {
  const theme = useUIStore((s) => s.theme)
  const toggleTheme = useUIStore((s) => s.toggleTheme)
  const routerState = useRouterState()
  const pathname = routerState.location.pathname
  const wsStatus = useConnectionStatus()
  const wsConnected = wsStatus === 'connected'

  // Build breadcrumb
  const segments = pathname === '/' ? ['/'] : pathname.replace(/\/$/, '').split('/').filter(Boolean)

  return (
    <header className="flex h-14 items-center justify-between border-b border-border bg-background px-6">
      {/* Breadcrumb */}
      <nav className="flex items-center gap-1.5 text-sm">
        <Link to="/" className="text-muted-foreground transition-colors hover:text-foreground">
          Kainex
        </Link>
        {segments.map((seg, i) => {
          const path = seg === '/' ? '/' : `/${segments.slice(0, i + 1).join('/')}`
          const label = routeLabels[path] || seg
          const isLast = i === segments.length - 1
          return (
            <span key={path} className="flex items-center gap-1.5">
              <span className="text-muted-foreground/50">/</span>
              {isLast ? (
                <span className="font-medium text-foreground">{label}</span>
              ) : (
                <Link to={path} className="text-muted-foreground transition-colors hover:text-foreground">
                  {label}
                </Link>
              )}
            </span>
          )
        })}
      </nav>

      {/* Right actions */}
      <div className="flex items-center gap-2">
        {/* WebSocket status */}
        <Tooltip>
          <TooltipTrigger asChild>
            <div className="flex items-center gap-1.5 px-2">
              <span
                className={`inline-block h-2 w-2 rounded-full ${wsConnected ? 'bg-profit' : 'bg-loss'}`}
              />
              {wsConnected ? (
                <Wifi className="h-3.5 w-3.5 text-muted-foreground" />
              ) : (
                <WifiOff className="h-3.5 w-3.5 text-muted-foreground" />
              )}
            </div>
          </TooltipTrigger>
          <TooltipContent side="bottom">
            {wsConnected ? '实时连接正常' : '实时连接已断开'}
          </TooltipContent>
        </Tooltip>

        <Separator orientation="vertical" className="h-5" />

        {/* Search trigger */}
        <Button variant="outline" size="sm" className="gap-2 text-muted-foreground" onClick={() => {}}>
          <Search className="h-3.5 w-3.5" />
          <span className="hidden sm:inline">搜索</span>
          <kbd className="pointer-events-none hidden h-5 select-none items-center gap-0.5 rounded border bg-muted px-1.5 font-mono text-[10px] font-medium sm:inline-flex">
            <span className="text-xs">\u2318</span>K
          </kbd>
        </Button>

        <Separator orientation="vertical" className="h-5" />

        {/* Theme toggle */}
        <Button variant="ghost" size="icon" onClick={toggleTheme}>
          {theme === 'dark' ? (
            <Sun className="h-4 w-4" />
          ) : (
            <Moon className="h-4 w-4" />
          )}
        </Button>
      </div>
    </header>
  )
}
