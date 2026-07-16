import { cn } from '../../lib/cn'
import { getIocTypeMeta } from '../../lib/iocTypes'

type IocTypeBadgeProps = {
  type: string
  className?: string
}

export function IocTypeBadge({ type, className }: IocTypeBadgeProps) {
  const { label, badgeClass } = getIocTypeMeta(type)
  return (
    <span
      className={cn(
        'inline-flex items-center border px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wider',
        'rounded-[2px]',
        badgeClass,
        className,
      )}
    >
      {label}
    </span>
  )
}
