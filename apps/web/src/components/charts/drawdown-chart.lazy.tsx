import { lazy, Suspense } from 'react'

const DrawdownChartInner = lazy(() =>
  import('./drawdown-chart').then((m) => ({ default: m.DrawdownChart })),
)

function ChartFallback({ height = 200 }: { height?: number }) {
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

export function DrawdownChart(props: React.ComponentProps<typeof DrawdownChartInner>) {
  return (
    <Suspense fallback={<ChartFallback height={props.height} />}>
      <DrawdownChartInner {...props} />
    </Suspense>
  )
}
