import { cn } from '@/lib/utils'

interface LoadingSkeletonProps {
  className?: string
  lines?: number
}

function Shimmer({ className }: { className?: string }) {
  return (
    <div
      className={cn(
        'animate-pulse rounded-md bg-muted',
        className,
      )}
    />
  )
}

export function LoadingSkeleton({ className, lines = 3 }: LoadingSkeletonProps) {
  return (
    <div className={cn('flex flex-1 flex-col items-center justify-center gap-6 p-8', className)}>
      <div className="w-full max-w-2xl space-y-4">
        <Shimmer className="h-8 w-1/3" />
        <div className="grid gap-4 md:grid-cols-4">
          {Array.from({ length: 4 }).map((_, i) => (
            <Shimmer key={i} className="h-24 w-full rounded-lg" />
          ))}
        </div>
        <Shimmer className="h-64 w-full rounded-lg" />
        {Array.from({ length: lines }).map((_, i) => (
          <Shimmer key={`line-${i}`} className={`h-4 ${i === 0 ? 'w-4/5' : i === 1 ? 'w-3/5' : 'w-2/5'}`} />
        ))}
      </div>
    </div>
  )
}
