import { cn } from '../../lib/cn'

type SkeletonProps = {
  className?: string
}

export function Skeleton({ className }: SkeletonProps) {
  return <div className={cn('shimmer h-4 rounded-[3px] bg-surface-2', className)} />
}

export function SkeletonCard() {
  return (
    <div className="panel-surface space-y-3 p-4">
      <Skeleton className="h-3 w-24" />
      <Skeleton className="h-5 w-3/4" />
      <Skeleton className="h-4 w-full" />
      <Skeleton className="h-4 w-2/3" />
    </div>
  )
}
