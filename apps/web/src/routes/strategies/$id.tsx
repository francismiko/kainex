import { createFileRoute } from '@tanstack/react-router'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'

export const Route = createFileRoute('/strategies/$id')({
  component: StrategyDetail,
})

function StrategyDetail() {
  const { id } = Route.useParams()

  return (
    <div className="space-y-6">
      <div className="flex items-center gap-3">
        <h1 className="text-2xl font-bold">策略详情</h1>
        <Badge>ID: {id}</Badge>
      </div>

      <div className="grid gap-4 md:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle>策略参数</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-sm text-muted-foreground">策略参数配置将在此展示</p>
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
