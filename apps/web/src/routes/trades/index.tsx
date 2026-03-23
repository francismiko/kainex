import { useState, useMemo, useCallback, Fragment } from 'react'
import { createFileRoute } from '@tanstack/react-router'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { LoadingSkeleton } from '@/components/shared/loading-skeleton'
import { useTrades, useTradeNotes, useCreateTradeNote } from '@/hooks/use-api'
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table'
import {
  useReactTable,
  getCoreRowModel,
  getSortedRowModel,
  getExpandedRowModel,
  flexRender,
  type ColumnDef,
  type SortingState,
  type ExpandedState,
} from '@tanstack/react-table'
import { ArrowUpDown, Download, ChevronRight, ChevronDown, Send } from 'lucide-react'

export const Route = createFileRoute('/trades/')({
  component: Trades,
})

interface TradeRow {
  id: string
  time: string
  strategy: string
  symbol: string
  side: '买入' | '卖出'
  price: number
  quantity: number
  fee: number
  pnl: number
}

const mockTrades: TradeRow[] = [
  { id: '1', time: '2026-03-23 10:32:15', strategy: 'SMA 交叉', symbol: 'BTC/USDT', side: '买入', price: 63150, quantity: 0.5, fee: 15.79, pnl: 0 },
  { id: '2', time: '2026-03-23 10:15:42', strategy: 'RSI 均值回归', symbol: 'ETH/USDT', side: '卖出', price: 3385, quantity: 5.0, fee: 8.46, pnl: 425.0 },
  { id: '3', time: '2026-03-23 09:45:03', strategy: '动量跟踪', symbol: 'AAPL', side: '买入', price: 188.50, quantity: 50, fee: 1.50, pnl: 0 },
  { id: '4', time: '2026-03-23 09:30:17', strategy: 'SMA 交叉', symbol: '贵州茅台', side: '买入', price: 1720, quantity: 100, fee: 51.60, pnl: 0 },
  { id: '5', time: '2026-03-23 09:15:28', strategy: '动量跟踪', symbol: 'TSLA', side: '卖出', price: 242.30, quantity: 30, fee: 1.16, pnl: 81.0 },
  { id: '6', time: '2026-03-22 15:42:11', strategy: 'RSI 均值回归', symbol: 'BTC/USDT', side: '买入', price: 62800, quantity: 0.3, fee: 9.42, pnl: 0 },
  { id: '7', time: '2026-03-22 14:28:33', strategy: 'SMA 交叉', symbol: 'ETH/USDT', side: '买入', price: 3410, quantity: 3.0, fee: 5.12, pnl: 0 },
  { id: '8', time: '2026-03-22 13:55:07', strategy: '动量跟踪', symbol: 'AAPL', side: '卖出', price: 186.00, quantity: 20, fee: 0.60, pnl: -64.0 },
  { id: '9', time: '2026-03-22 11:32:44', strategy: 'RSI 均值回归', symbol: '贵州茅台', side: '买入', price: 1690, quantity: 50, fee: 25.35, pnl: 0 },
  { id: '10', time: '2026-03-22 10:18:59', strategy: 'SMA 交叉', symbol: 'TSLA', side: '卖出', price: 244.10, quantity: 15, fee: 0.58, pnl: 34.5 },
  { id: '11', time: '2026-03-21 15:05:22', strategy: '动量跟踪', symbol: 'BTC/USDT', side: '卖出', price: 63500, quantity: 0.2, fee: 6.35, pnl: 156.0 },
  { id: '12', time: '2026-03-21 14:22:18', strategy: 'RSI 均值回归', symbol: 'ETH/USDT', side: '买入', price: 3350, quantity: 8.0, fee: 13.40, pnl: 0 },
  { id: '13', time: '2026-03-21 13:11:45', strategy: 'SMA 交叉', symbol: 'AAPL', side: '买入', price: 184.20, quantity: 40, fee: 1.18, pnl: 0 },
  { id: '14', time: '2026-03-21 11:55:33', strategy: '动量跟踪', symbol: '贵州茅台', side: '卖出', price: 1710, quantity: 30, fee: 15.39, pnl: 600.0 },
  { id: '15', time: '2026-03-21 10:40:07', strategy: 'RSI 均值回归', symbol: 'TSLA', side: '买入', price: 248.00, quantity: 25, fee: 0.99, pnl: 0 },
  { id: '16', time: '2026-03-20 15:30:19', strategy: 'SMA 交叉', symbol: 'BTC/USDT', side: '买入', price: 61200, quantity: 0.4, fee: 12.24, pnl: 0 },
  { id: '17', time: '2026-03-20 14:15:52', strategy: '动量跟踪', symbol: 'ETH/USDT', side: '卖出', price: 3300, quantity: 6.0, fee: 9.90, pnl: -180.0 },
  { id: '18', time: '2026-03-20 13:02:41', strategy: 'RSI 均值回归', symbol: 'AAPL', side: '卖出', price: 183.50, quantity: 35, fee: 1.03, pnl: -52.5 },
  { id: '19', time: '2026-03-20 11:48:15', strategy: 'SMA 交叉', symbol: '贵州茅台', side: '买入', price: 1675, quantity: 80, fee: 40.20, pnl: 0 },
  { id: '20', time: '2026-03-20 10:30:28', strategy: '动量跟踪', symbol: 'TSLA', side: '买入', price: 250.00, quantity: 20, fee: 0.80, pnl: 0 },
]

function apiTradesToDisplay(trades: { id: string; symbol: string; side: string; price: number; quantity: number; timestamp: string; strategyId: string }[]): TradeRow[] {
  return trades.map((t) => ({
    id: t.id,
    time: t.timestamp,
    strategy: t.strategyId,
    symbol: t.symbol,
    side: t.side === 'buy' ? '买入' as const : '卖出' as const,
    price: t.price,
    quantity: t.quantity,
    fee: 0,
    pnl: 0,
  }))
}

const columns: ColumnDef<TradeRow>[] = [
  {
    id: 'expand',
    header: '',
    cell: ({ row }) => (
      <button
        className="p-1 rounded hover:bg-muted"
        onClick={(e) => {
          e.stopPropagation()
          row.toggleExpanded()
        }}
      >
        {row.getIsExpanded() ? (
          <ChevronDown className="h-4 w-4 text-muted-foreground" />
        ) : (
          <ChevronRight className="h-4 w-4 text-muted-foreground" />
        )}
      </button>
    ),
    size: 32,
  },
  {
    accessorKey: 'time',
    header: ({ column }) => (
      <button className="flex items-center gap-1" onClick={() => column.toggleSorting()}>
        时间 <ArrowUpDown className="h-3 w-3" />
      </button>
    ),
    cell: ({ getValue }) => <span className="whitespace-nowrap font-mono text-xs">{getValue<string>()}</span>,
  },
  {
    accessorKey: 'strategy',
    header: '策略',
  },
  {
    accessorKey: 'symbol',
    header: '标的',
    cell: ({ getValue }) => <span className="font-medium">{getValue<string>()}</span>,
  },
  {
    accessorKey: 'side',
    header: '方向',
    cell: ({ getValue }) => {
      const side = getValue<string>()
      return (
        <span className={`font-medium ${side === '买入' ? 'text-profit' : 'text-loss'}`}>
          {side}
        </span>
      )
    },
  },
  {
    accessorKey: 'price',
    header: ({ column }) => (
      <button className="flex items-center gap-1" onClick={() => column.toggleSorting()}>
        价格 <ArrowUpDown className="h-3 w-3" />
      </button>
    ),
    cell: ({ getValue }) => <span className="font-mono">{getValue<number>().toLocaleString()}</span>,
  },
  {
    accessorKey: 'quantity',
    header: '数量',
    cell: ({ getValue }) => <span className="font-mono">{getValue<number>()}</span>,
  },
  {
    accessorKey: 'fee',
    header: '手续费',
    cell: ({ getValue }) => <span className="font-mono text-muted-foreground">{getValue<number>().toFixed(2)}</span>,
  },
  {
    accessorKey: 'pnl',
    header: ({ column }) => (
      <button className="flex items-center gap-1" onClick={() => column.toggleSorting()}>
        盈亏 <ArrowUpDown className="h-3 w-3" />
      </button>
    ),
    cell: ({ getValue }) => {
      const v = getValue<number>()
      if (v === 0) return <span className="font-mono text-muted-foreground">-</span>
      return (
        <span className={`font-mono font-medium ${v > 0 ? 'text-profit' : 'text-loss'}`}>
          {v > 0 ? '+' : ''}{v.toFixed(2)}
        </span>
      )
    },
  },
]

function TradeNotesPanel({ tradeId }: { tradeId: string }) {
  const [noteText, setNoteText] = useState('')
  const { data: notes, isLoading } = useTradeNotes(tradeId)
  const createNote = useCreateTradeNote()

  const handleSubmit = () => {
    const trimmed = noteText.trim()
    if (!trimmed) return
    createNote.mutate({ tradeId, content: trimmed })
    setNoteText('')
  }

  return (
    <div className="px-8 py-3 bg-muted/30 space-y-3">
      <p className="text-xs font-medium text-muted-foreground">交易笔记</p>
      {isLoading ? (
        <p className="text-xs text-muted-foreground">加载中...</p>
      ) : notes && notes.length > 0 ? (
        <ul className="space-y-2">
          {notes.map((note) => (
            <li key={note.id} className="text-sm">
              <span className="text-muted-foreground text-xs mr-2">
                {new Date(note.created_at).toLocaleString('zh-CN')}
              </span>
              {note.content}
            </li>
          ))}
        </ul>
      ) : (
        <p className="text-xs text-muted-foreground">暂无笔记</p>
      )}
      <div className="flex gap-2">
        <Input
          placeholder="添加笔记..."
          value={noteText}
          onChange={(e) => setNoteText(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
              e.preventDefault()
              handleSubmit()
            }
          }}
          className="h-8 text-sm"
        />
        <Button
          size="sm"
          variant="outline"
          onClick={handleSubmit}
          disabled={!noteText.trim() || createNote.isPending}
          className="h-8 px-3"
        >
          <Send className="h-3 w-3" />
        </Button>
      </div>
    </div>
  )
}

function exportTradesCSV(rows: TradeRow[]) {
  const header = ['时间', '策略', '标的', '方向', '价格', '数量', '手续费', '盈亏']
  const csvRows = [
    header.join(','),
    ...rows.map((r) =>
      [r.time, r.strategy, r.symbol, r.side, r.price, r.quantity, r.fee, r.pnl].join(','),
    ),
  ]
  const csvContent = '\uFEFF' + csvRows.join('\n')
  const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' })
  const url = URL.createObjectURL(blob)
  const now = new Date()
  const ymd = `${now.getFullYear()}${String(now.getMonth() + 1).padStart(2, '0')}${String(now.getDate()).padStart(2, '0')}`
  const a = document.createElement('a')
  a.href = url
  a.download = `kainex-trades-${ymd}.csv`
  document.body.appendChild(a)
  a.click()
  document.body.removeChild(a)
  URL.revokeObjectURL(url)
}

function Trades() {
  const [sorting, setSorting] = useState<SortingState>([{ id: 'time', desc: true }])
  const [expanded, setExpanded] = useState<ExpandedState>({})
  const { data, isLoading, isError } = useTrades()

  const trades = useMemo(
    () => (data ? apiTradesToDisplay(data) : mockTrades),
    [data],
  )

  const table = useReactTable({
    data: trades,
    columns,
    state: { sorting, expanded },
    onSortingChange: setSorting,
    onExpandedChange: setExpanded,
    getRowCanExpand: () => true,
    getCoreRowModel: getCoreRowModel(),
    getSortedRowModel: getSortedRowModel(),
    getExpandedRowModel: getExpandedRowModel(),
  })

  const handleExportCSV = useCallback(() => {
    exportTradesCSV(table.getSortedRowModel().rows.map((r) => r.original))
  }, [table])

  if (isLoading) return <LoadingSkeleton />

  return (
    <div className="space-y-6">
      <div className="flex items-center gap-3">
        <h1 className="text-2xl font-bold">交易记录</h1>
        {isError && (
          <Badge variant="outline" className="text-muted-foreground">
            展示示例数据
          </Badge>
        )}
      </div>

      <Card>
        <CardHeader className="flex flex-row items-center justify-between">
          <CardTitle>历史成交</CardTitle>
          <Button variant="outline" size="sm" onClick={handleExportCSV}>
            <Download className="h-4 w-4" />
            导出 CSV
          </Button>
        </CardHeader>
        <CardContent>
          <div className="overflow-x-auto">
            <Table>
              <TableHeader>
                {table.getHeaderGroups().map((headerGroup) => (
                  <TableRow key={headerGroup.id}>
                    {headerGroup.headers.map((header) => (
                      <TableHead key={header.id}>
                        {header.isPlaceholder
                          ? null
                          : flexRender(header.column.columnDef.header, header.getContext())}
                      </TableHead>
                    ))}
                  </TableRow>
                ))}
              </TableHeader>
              <TableBody>
                {table.getRowModel().rows.map((row) => (
                  <Fragment key={row.id}>
                    <TableRow
                      className="cursor-pointer"
                      onClick={() => row.toggleExpanded()}
                    >
                      {row.getVisibleCells().map((cell) => (
                        <TableCell key={cell.id}>
                          {flexRender(cell.column.columnDef.cell, cell.getContext())}
                        </TableCell>
                      ))}
                    </TableRow>
                    {row.getIsExpanded() && (
                      <TableRow>
                        <TableCell colSpan={columns.length} className="p-0">
                          <TradeNotesPanel tradeId={row.original.id} />
                        </TableCell>
                      </TableRow>
                    )}
                  </Fragment>
                ))}
              </TableBody>
            </Table>
          </div>
        </CardContent>
      </Card>
    </div>
  )
}
