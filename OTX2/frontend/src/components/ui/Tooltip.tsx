import type { ReactNode } from 'react'
import { cn } from '../../lib/cn'

type TooltipProps = {
  label: string
  children: ReactNode
  className?: string
}

// Lightweight CSS-only tooltip: appears on hover/focus of the wrapped element.
export function Tooltip({ label, children, className }: TooltipProps) {
  return (
    <span className={cn('group/tooltip relative inline-flex', className)}>
      {children}
      <span
        role="tooltip"
        className="pointer-events-none absolute bottom-full left-0 z-30 mb-1 hidden max-w-md whitespace-pre-wrap break-all border border-line bg-surface-0 px-2 py-1 font-data text-[10px] text-neutral-200 shadow-lg group-hover/tooltip:block group-focus-within/tooltip:block"
      >
        {label}
      </span>
    </span>
  )
}
