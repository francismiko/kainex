import { createFileRoute } from '@tanstack/react-router'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'

export const Route = createFileRoute('/risk/')({
  component: Risk,
})

function Risk() {
  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold">风控监控</h1>

      <div className="grid gap-4 md:grid-cols-3">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground">回撤熔断</CardTitle>
            <Badge variant="outline" className="text-green-500 border-green-500">正常</Badge>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">-3.2%</div>
            <p className="text-xs text-muted-foreground">阈值: -15%</p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="flex flex-row items-center justify-between pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground">仓位使用</CardTitle>
            <Badge variant="outline" className="text-yellow-500 border-yellow-500">警告</Badge>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">78%</div>
            <p className="text-xs text-muted-foreground">阈值: 80%</p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="flex flex-row items-center justify-between pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground">日内亏损</CardTitle>
            <Badge variant="outline" className="text-green-500 border-green-500">正常</Badge>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">-¥ 2,340</div>
            <p className="text-xs text-muted-foreground">阈值: -¥ 50,000</p>
          </CardContent>
        </Card>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>风险事件日志</CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-sm text-muted-foreground">风控触发记录将在此展示</p>
        </CardContent>
      </Card>
    </div>
  )
}
