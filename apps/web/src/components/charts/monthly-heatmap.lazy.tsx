import { lazy, Suspense } from 'react'

const MonthlyHeatmapInner = lazy(() =>
  import('./monthly-heatmap').then((m) => ({ default: m.MonthlyHeatmap })),
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

export function MonthlyHeatmap(props: React.ComponentProps<typeof MonthlyHeatmapInner>) {
  return (
    <Suspense fallback={<ChartFallback height={props.height} />}>
      <MonthlyHeatmapInner {...props} />
    </Suspense>
  )
}
