import { createFileRoute } from '@tanstack/react-router'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { LoadingSkeleton } from '@/components/shared/loading-skeleton'
import { useStrategy, useStartStrategy, useStopStrategy } from '@/hooks/use-api'
import { Button } from '@/components/ui/button'

export const Route = createFileRoute('/strategies/$id')({
  component: StrategyDetail,
})

function StrategyDetail() {
  const { id } = Route.useParams()
  const { data: strategy, isLoading, isError } = useStrategy(id)
  const startMutation = useStartStrategy()
  const stopMutation = useStopStrategy()

  if (isLoading) return <LoadingSkeleton />

  return (
    <div className="space-y-6">
      <div className="flex items-center gap-3">
        <h1 className="text-2xl font-bold">策略详情</h1>
        <Badge>ID: {id}</Badge>
        {isError && (
          <Badge variant="outline" className="text-muted-foreground">
            无法连接后端
          </Badge>
        )}
      </div>

      {strategy && (
        <div className="flex items-center gap-3">
          <Badge
            variant={
              strategy.status === 'running'
                ? 'default'
                : strategy.status === 'error'
                  ? 'destructive'
                  : 'outline'
            }
          >
            {strategy.status === 'running' ? '运行中' : strategy.status === 'error' ? '异常' : '已停止'}
          </Badge>
          {strategy.status === 'stopped' && (
            <Button
              size="sm"
              onClick={() => startMutation.mutate(id)}
              disabled={startMutation.isPending}
            >
              启动
            </Button>
          )}
          {strategy.status === 'running' && (
            <Button
              size="sm"
              variant="outline"
              onClick={() => stopMutation.mutate(id)}
              disabled={stopMutation.isPending}
            >
              停止
            </Button>
          )}
        </div>
      )}

      <div className="grid gap-4 md:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle>策略参数</CardTitle>
          </CardHeader>
          <CardContent>
            {strategy ? (
              <dl className="space-y-2 text-sm">
                <div className="flex justify-between">
                  <dt className="text-muted-foreground">名称</dt>
                  <dd>{strategy.name}</dd>
                </div>
                <div className="flex justify-between">
                  <dt className="text-muted-foreground">市场</dt>
                  <dd>{strategy.market}</dd>
                </div>
                <div className="flex justify-between">
                  <dt className="text-muted-foreground">标的</dt>
                  <dd>{strategy.symbols.join(', ')}</dd>
                </div>
                <div className="flex justify-between">
                  <dt className="text-muted-foreground">描述</dt>
                  <dd>{strategy.description || '-'}</dd>
                </div>
              </dl>
            ) : (
              <p className="text-sm text-muted-foreground">策略参数配置将在此展示</p>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>实时信号</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-sm text-muted-foreground">策略生成的实时交易信号将在此展示</p>
          </CardContent>
        </Card>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>回测结果</CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-sm text-muted-foreground">选择时间范围后运行回测，结果将在此展示</p>
        </CardContent>
      </Card>
    </div>
  )
}
