import { lazy, Suspense } from 'react'

const AllocationChartInner = lazy(() =>
  import('./allocation-chart').then((m) => ({ default: m.AllocationChart })),
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

export function AllocationChart(props: React.ComponentProps<typeof AllocationChartInner>) {
  return (
    <Suspense fallback={<ChartFallback height={props.height} />}>
      <AllocationChartInner {...props} />
    </Suspense>
  )
}
