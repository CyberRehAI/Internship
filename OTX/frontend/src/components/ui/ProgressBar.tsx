import { cn } from '../../lib/cn'

type ProgressBarProps = {
  value?: number
  indeterminate?: boolean
  className?: string
}

export function ProgressBar({ value = 0, indeterminate = false, className }: ProgressBarProps) {
  if (indeterminate) {
    return (
      <div
        className={cn('progress-track', className)}
        role="progressbar"
        aria-busy="true"
        aria-label="Loading"
      >
        <div className="progress-indeterminate" />
      </div>
    )
  }

  return (
    <progress
      className={cn('progress-bar', className)}
      value={Math.min(100, Math.max(0, value))}
      max={100}
      aria-label="Progress"
    />
  )
}
