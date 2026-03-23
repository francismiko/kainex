import { createFileRoute } from '@tanstack/react-router'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Separator } from '@/components/ui/separator'
import { Switch } from '@/components/ui/switch'
import { Badge } from '@/components/ui/badge'
import { useUIStore } from '@/stores/ui-store'
import { useConnectionStatus } from '@/hooks/use-websocket'
import { Moon, Sun, Wifi, WifiOff, ArrowUpRight, ArrowDownRight } from 'lucide-react'

export const Route = createFileRoute('/settings/')({
  component: Settings,
})

function Settings() {
  const theme = useUIStore((s) => s.theme)
  const toggleTheme = useUIStore((s) => s.toggleTheme)
  const colorScheme = useUIStore((s) => s.colorScheme)
  const toggleColorScheme = useUIStore((s) => s.toggleColorScheme)
  const wsStatus = useConnectionStatus()

  const apiBase =
    (import.meta.env.VITE_API_BASE_URL as string | undefined) ??
    'http://localhost:8001'

  return (
    <div className="mx-auto max-w-2xl space-y-6">
      <h1 className="text-2xl font-bold">{'设置'}</h1>

      {/* Appearance */}
      <Card>
        <CardHeader>
          <CardTitle>{'外观'}</CardTitle>
        </CardHeader>
        <CardContent className="space-y-6">
          {/* Theme toggle */}
          <div className="flex items-center justify-between">
            <div className="space-y-0.5">
              <div className="text-sm font-medium">{'暗色模式'}</div>
              <div className="text-xs text-muted-foreground">
                {'切换暗色 / 亮色主题'}
              </div>
            </div>
            <div className="flex items-center gap-2">
              <Sun className="h-4 w-4 text-muted-foreground" />
              <Switch
                checked={theme === 'dark'}
                onCheckedChange={toggleTheme}
              />
              <Moon className="h-4 w-4 text-muted-foreground" />
            </div>
          </div>

          <Separator />

          {/* Color scheme toggle */}
          <div className="flex items-center justify-between">
            <div className="space-y-0.5">
              <div className="text-sm font-medium">{'涨跌配色'}</div>
              <div className="text-xs text-muted-foreground">
                {colorScheme === 'international'
                  ? '国际：绿涨红跌'
                  : '中国：红涨绿跌'}
              </div>
            </div>
            <div className="flex items-center gap-3">
              {/* Preview chips */}
              <div className="flex items-center gap-1.5 text-xs">
                <span className="flex items-center gap-0.5 font-mono">
                  <ArrowUpRight className="h-3 w-3" style={{ color: 'var(--profit)' }} />
                  <span style={{ color: 'var(--profit)' }}>{'涨'}</span>
                </span>
                <span className="flex items-center gap-0.5 font-mono">
                  <ArrowDownRight className="h-3 w-3" style={{ color: 'var(--loss)' }} />
                  <span style={{ color: 'var(--loss)' }}>{'跌'}</span>
                </span>
              </div>
              <Switch
                checked={colorScheme === 'chinese'}
                onCheckedChange={toggleColorScheme}
              />
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Connection */}
      <Card>
        <CardHeader>
          <CardTitle>{'连接'}</CardTitle>
        </CardHeader>
        <CardContent className="space-y-6">
          {/* API Base URL */}
          <div className="flex items-center justify-between">
            <div className="space-y-0.5">
              <div className="text-sm font-medium">{'API 地址'}</div>
              <div className="text-xs text-muted-foreground">
                {'后端服务接口地址'}
              </div>
            </div>
            <code className="rounded bg-muted px-2 py-1 text-xs">
              {apiBase}
            </code>
          </div>

          <Separator />

          {/* WebSocket status */}
          <div className="flex items-center justify-between">
            <div className="space-y-0.5">
              <div className="text-sm font-medium">{'WebSocket 状态'}</div>
              <div className="text-xs text-muted-foreground">
                {'实时数据推送连接'}
              </div>
            </div>
            <div className="flex items-center gap-2">
              {wsStatus === 'connected' ? (
                <Wifi className="h-4 w-4 text-profit" />
              ) : (
                <WifiOff className="h-4 w-4 text-loss" />
              )}
              <Badge
                variant={wsStatus === 'connected' ? 'default' : 'destructive'}
              >
                {wsStatus === 'connected'
                  ? '已连接'
                  : wsStatus === 'connecting'
                    ? '连接中...'
                    : '已断开'}
              </Badge>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* About */}
      <Card>
        <CardHeader>
          <CardTitle>{'关于'}</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="flex items-center justify-between">
            <span className="text-sm text-muted-foreground">{'版本'}</span>
            <span className="text-sm font-mono">0.0.0</span>
          </div>
          <Separator />
          <div className="space-y-2">
            <span className="text-sm text-muted-foreground">{'技术栈'}</span>
            <div className="flex flex-wrap gap-1.5">
              {[
                'React 19',
                'TanStack Router',
                'TanStack Query',
                'Zustand',
                'Tailwind CSS 4',
                'shadcn/ui',
                'ECharts',
                'Lightweight Charts',
              ].map((tech) => (
                <Badge key={tech} variant="secondary" className="text-xs">
                  {tech}
                </Badge>
              ))}
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  )
}
