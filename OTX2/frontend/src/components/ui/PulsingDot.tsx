import { cn } from '../../lib/cn'

type PulsingDotProps = {
  status: 'connected' | 'error' | 'loading'
  className?: string
}

const statusClasses = {
  connected: 'bg-success',
  error: 'bg-danger',
  loading: 'bg-warning',
}

export function PulsingDot({ status, className }: PulsingDotProps) {
  return (
    <span className={cn('relative inline-flex h-2 w-2', className)} aria-hidden="true">
      <span className={cn('absolute inline-flex h-full w-full animate-ping rounded-full opacity-60', statusClasses[status])} />
      <span className={cn('relative inline-flex h-2 w-2 rounded-full', statusClasses[status])} />
    </span>
  )
}
