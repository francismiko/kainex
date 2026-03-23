import { useState } from 'react'
import { createFileRoute } from '@tanstack/react-router'
import { toast } from 'sonner'
import { Bell, Plus, Trash2 } from 'lucide-react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Switch } from '@/components/ui/switch'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from '@/components/ui/dialog'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table'
import { LoadingSkeleton } from '@/components/shared/loading-skeleton'
import { EmptyState } from '@/components/shared/empty-state'
import { useAlerts, useCreateAlert, useDeleteAlert, useUpdateAlert } from '@/hooks/use-api'
import type { AlertCreateInput, AlertItem } from '@/lib/api-client'

export const Route = createFileRoute('/alerts/')({
  component: Alerts,
})

const CONDITION_LABELS: Record<string, string> = {
  above: '高于',
  below: '低于',
  cross_above: '上穿',
  cross_below: '下穿',
}

const SYMBOLS = [
  'BTC/USDT',
  'ETH/USDT',
  'SOL/USDT',
  'BNB/USDT',
  'AAPL',
  'TSLA',
  'GOOGL',
]

const MARKETS = [
  { value: 'crypto', label: '加密货币' },
  { value: 'stock', label: '股票' },
]

function CreateAlertDialog() {
  const [open, setOpen] = useState(false)
  const [symbol, setSymbol] = useState('')
  const [market, setMarket] = useState('crypto')
  const [condition, setCondition] = useState<AlertCreateInput['condition']>('above')
  const [price, setPrice] = useState('')
  const [message, setMessage] = useState('')

  const createAlert = useCreateAlert()

  const handleSubmit = () => {
    if (!symbol || !price) {
      toast.error('请填写标的和目标价格')
      return
    }
    const priceNum = parseFloat(price)
    if (isNaN(priceNum) || priceNum <= 0) {
      toast.error('请输入有效的价格')
      return
    }

    createAlert.mutate(
      {
        symbol,
        market,
        condition,
        price: priceNum,
        message: message || undefined,
      },
      {
        onSuccess: () => {
          toast.success('告警创建成功')
          setOpen(false)
          setSymbol('')
          setPrice('')
          setMessage('')
          setCondition('above')
          setMarket('crypto')
        },
        onError: (err) => {
          toast.error(`创建失败: ${err.message}`)
        },
      },
    )
  }

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger asChild>
        <Button>
          <Plus className="h-4 w-4" />
          新建告警
        </Button>
      </DialogTrigger>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>创建价格告警</DialogTitle>
          <DialogDescription>
            设置价格条件，当条件触发时将通过 WebSocket 推送通知。
          </DialogDescription>
        </DialogHeader>

        <div className="grid gap-4 py-4">
          <div className="grid gap-2">
            <label className="text-sm font-medium">市场</label>
            <Select value={market} onValueChange={setMarket}>
              <SelectTrigger className="w-full">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {MARKETS.map((m) => (
                  <SelectItem key={m.value} value={m.value}>
                    {m.label}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          <div className="grid gap-2">
            <label className="text-sm font-medium">标的</label>
            <Select value={symbol} onValueChange={setSymbol}>
              <SelectTrigger className="w-full">
                <SelectValue placeholder="选择标的" />
              </SelectTrigger>
              <SelectContent>
                {SYMBOLS.map((s) => (
                  <SelectItem key={s} value={s}>
                    {s}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          <div className="grid gap-2">
            <label className="text-sm font-medium">触发条件</label>
            <Select
              value={condition}
              onValueChange={(v) => setCondition(v as AlertCreateInput['condition'])}
            >
              <SelectTrigger className="w-full">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="above">高于 (Above)</SelectItem>
                <SelectItem value="below">低于 (Below)</SelectItem>
                <SelectItem value="cross_above">上穿 (Cross Above)</SelectItem>
                <SelectItem value="cross_below">下穿 (Cross Below)</SelectItem>
              </SelectContent>
            </Select>
          </div>

          <div className="grid gap-2">
            <label className="text-sm font-medium">目标价格</label>
            <Input
              type="number"
              placeholder="0.00"
              value={price}
              onChange={(e) => setPrice(e.target.value)}
              step="any"
              min="0"
            />
          </div>

          <div className="grid gap-2">
            <label className="text-sm font-medium">备注</label>
            <Input
              placeholder="可选的提醒消息..."
              value={message}
              onChange={(e) => setMessage(e.target.value)}
            />
          </div>
        </div>

        <DialogFooter>
          <Button variant="outline" onClick={() => setOpen(false)}>
            取消
          </Button>
          <Button onClick={handleSubmit} disabled={createAlert.isPending}>
            {createAlert.isPending ? '创建中...' : '创建'}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}

function AlertRow({ alert }: { alert: AlertItem }) {
  const deleteAlert = useDeleteAlert()
  const updateAlert = useUpdateAlert()

  const handleToggle = (checked: boolean) => {
    updateAlert.mutate(
      { id: alert.id, data: { enabled: checked } },
      {
        onError: (err) => toast.error(`更新失败: ${err.message}`),
      },
    )
  }

  const handleDelete = () => {
    deleteAlert.mutate(alert.id, {
      onSuccess: () => toast.success('告警已删除'),
      onError: (err) => toast.error(`删除失败: ${err.message}`),
    })
  }

  return (
    <TableRow>
      <TableCell className="font-medium">{alert.symbol}</TableCell>
      <TableCell>
        <Badge variant="outline">
          {CONDITION_LABELS[alert.condition] ?? alert.condition}
        </Badge>
      </TableCell>
      <TableCell className="font-mono">
        {alert.price.toLocaleString()}
      </TableCell>
      <TableCell className="text-muted-foreground max-w-[200px] truncate">
        {alert.message || '-'}
      </TableCell>
      <TableCell>
        {alert.triggered ? (
          <Badge variant="destructive">已触发</Badge>
        ) : alert.enabled ? (
          <Badge variant="default">启用</Badge>
        ) : (
          <Badge variant="secondary">已禁用</Badge>
        )}
      </TableCell>
      <TableCell>
        <div className="flex items-center gap-3">
          <Switch
            checked={alert.enabled}
            onCheckedChange={handleToggle}
            disabled={updateAlert.isPending || alert.triggered}
            size="sm"
          />
          <Button
            variant="ghost"
            size="sm"
            onClick={handleDelete}
            disabled={deleteAlert.isPending}
            className="text-muted-foreground hover:text-destructive"
          >
            <Trash2 className="h-4 w-4" />
          </Button>
        </div>
      </TableCell>
    </TableRow>
  )
}

function Alerts() {
  const { data: alerts, isLoading, isError } = useAlerts()

  if (isLoading) return <LoadingSkeleton />

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <h1 className="text-2xl font-bold">价格告警</h1>
          {isError && (
            <Badge variant="outline" className="text-muted-foreground">
              API 不可用
            </Badge>
          )}
        </div>
        <CreateAlertDialog />
      </div>

      <Card>
        <CardHeader>
          <CardTitle>告警列表</CardTitle>
        </CardHeader>
        <CardContent>
          {!alerts || alerts.length === 0 ? (
            <EmptyState
              icon={Bell}
              title="暂无告警"
              description="创建你的第一个价格告警，当条件触发时将收到通知。"
            />
          ) : (
            <div className="overflow-x-auto">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>标的</TableHead>
                    <TableHead>条件</TableHead>
                    <TableHead>目标价</TableHead>
                    <TableHead>备注</TableHead>
                    <TableHead>状态</TableHead>
                    <TableHead>操作</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {alerts.map((alert) => (
                    <AlertRow key={alert.id} alert={alert} />
                  ))}
                </TableBody>
              </Table>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  )
}
