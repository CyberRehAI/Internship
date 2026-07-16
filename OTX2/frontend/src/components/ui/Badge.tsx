import { cn } from '../../lib/cn'

type BadgeProps = {
  children: string
  className?: string
}

export function Badge({ children, className }: BadgeProps) {
  return (
    <span
      className={cn(
        'inline-flex items-center border border-line bg-surface-2 px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wider text-neutral-400',
        'rounded-[3px]',
        className,
      )}
    >
      {children}
    </span>
  )
}

const tlpColors: Record<string, string> = {
  red: 'border-danger/50 bg-danger/10 text-danger',
  amber: 'border-warning/50 bg-warning/10 text-warning',
  green: 'border-success/50 bg-success/10 text-success',
  white: 'border-neutral-400/50 bg-neutral-400/10 text-neutral-200',
}

export function TlpBadge({ value }: { value?: string }) {
  const key = (value || 'green').toLowerCase()
  return (
    <span
      className={cn(
        'inline-flex items-center border px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wider',
        'rounded-[3px]',
        tlpColors[key] ?? tlpColors.green,
      )}
    >
      TLP:{value?.toUpperCase() || 'GREEN'}
    </span>
  )
}
