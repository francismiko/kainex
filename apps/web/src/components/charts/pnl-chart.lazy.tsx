import { lazy, Suspense } from 'react'

const PnlChartInner = lazy(() =>
  import('./pnl-chart').then((m) => ({ default: m.PnlChart })),
)

function ChartFallback({ height = 300 }: { height?: number }) {
  return (
    <div
      className="flex items-center justify-center rounded-md bg-muted/30"
      style={{ height }}
    >
      <div className="animate-pulse text-sm text-muted-foreground">
        Loading chart...
      </div>
    </div>
  )
}

export function PnlChart(props: React.ComponentProps<typeof PnlChartInner>) {
  return (
    <Suspense fallback={<ChartFallback height={props.height} />}>
      <PnlChartInner {...props} />
    </Suspense>
  )
}
