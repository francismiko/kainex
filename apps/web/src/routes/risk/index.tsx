import { createFileRoute } from '@tanstack/react-router'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Progress } from '@/components/ui/progress'
import { Alert, AlertTitle, AlertDescription } from '@/components/ui/alert'

export const Route = createFileRoute('/risk/')({
  component: Risk,
})

interface RiskMetric {
  label: string
  currentValue: number
  currentDisplay: string
  threshold: number
  thresholdDisplay: string
  status: 'normal' | 'warning' | 'danger'
  /** Progress percentage: currentValue / threshold * 100 */
  progress: number
}

const riskMetrics: RiskMetric[] = [
  {
    label: '回撤熔断',
    currentValue: 3.2,
    currentDisplay: '-3.2%',
    threshold: 15,
    thresholdDisplay: '-15%',
    status: 'normal',
    progress: (3.2 / 15) * 100,
  },
  {
    label: '仓位使用',
    currentValue: 78,
    currentDisplay: '78%',
    threshold: 80,
    thresholdDisplay: '80%',
    status: 'warning',
    progress: (78 / 80) * 100,
  },
  {
    label: '日内亏损',
    currentValue: 2340,
    currentDisplay: '-\u00a52,340',
    threshold: 50000,
    thresholdDisplay: '-\u00a550,000',
    status: 'normal',
    progress: (2340 / 50000) * 100,
  },
]

interface RiskEvent {
  id: string
  timestamp: string
  severity: 'info' | 'warning' | 'critical'
  message: string
}

const mockEvents: RiskEvent[] = [
  { id: '1', timestamp: '2026-03-23 14:32:10', severity: 'warning', message: '仓位使用率接近阈值 (78%)，已触发预警' },
  { id: '2', timestamp: '2026-03-23 11:05:43', severity: 'info', message: '风控参数已更新：日内亏损阈值调整为 \u00a550,000' },
  { id: '3', timestamp: '2026-03-22 16:48:21', severity: 'critical', message: '策略 alpha-momentum 触发回撤熔断，已自动停止' },
  { id: '4', timestamp: '2026-03-22 09:12:05', severity: 'info', message: '每日风控检查完成，所有指标正常' },
  { id: '5', timestamp: '2026-03-21 15:30:17', severity: 'warning', message: '单笔交易亏损 \u00a58,200 超过单笔限额 80%' },
]

const statusConfig = {
  normal: { label: '正常', className: 'text-profit border-profit' },
  warning: { label: '警告', className: 'text-yellow-500 border-yellow-500' },
  danger: { label: '危险', className: 'text-loss border-loss' },
} as const

const severityConfig = {
  info: { color: 'var(--color-muted-foreground)', dot: 'bg-muted-foreground' },
  warning: { color: 'var(--color-chart-4, #eab308)', dot: 'bg-yellow-500' },
  critical: { color: 'var(--color-loss)', dot: 'bg-loss' },
} as const

function Risk() {
  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold">风控监控</h1>

      <div className="grid gap-4 md:grid-cols-3">
        {riskMetrics.map((metric) => {
          const config = statusConfig[metric.status]
          return (
            <Card key={metric.label}>
              <CardHeader className="flex flex-row items-center justify-between pb-2">
                <CardTitle className="text-sm font-medium text-muted-foreground">
                  {metric.label}
                </CardTitle>
                <Badge variant="outline" className={config.className}>
                  {config.label}
                </Badge>
              </CardHeader>
              <CardContent className="space-y-3">
                <div className="text-2xl font-bold">{metric.currentDisplay}</div>
                <Progress value={metric.progress} />
                <p className="text-xs text-muted-foreground">
                  阈值: {metric.thresholdDisplay} ({metric.progress.toFixed(0)}%)
                </p>
              </CardContent>
            </Card>
          )
        })}
      </div>

      <Card>
        <CardHeader>
          <CardTitle>风险事件日志</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-3">
            {mockEvents.map((event) => {
              const config = severityConfig[event.severity]
              return (
                <Alert key={event.id} variant={event.severity === 'critical' ? 'destructive' : 'default'}>
                  <div className={`h-3 w-3 rounded-full ${config.dot} mt-0.5`} />
                  <AlertTitle className="flex items-center gap-2">
                    <span className="text-xs text-muted-foreground font-normal">{event.timestamp}</span>
                    <Badge
                      variant="outline"
                      className="text-xs px-1.5 py-0"
                      style={{ color: config.color, borderColor: config.color }}
                    >
                      {event.severity === 'info' ? '信息' : event.severity === 'warning' ? '警告' : '严重'}
                    </Badge>
                  </AlertTitle>
                  <AlertDescription>{event.message}</AlertDescription>
                </Alert>
              )
            })}
          </div>
        </CardContent>
      </Card>
    </div>
  )
}
