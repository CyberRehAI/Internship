import type { ReactNode } from 'react'
import { cn } from '../../lib/cn'

type ScrollFadeProps = {
  children: ReactNode
  className?: string
}

export function ScrollFade({ children, className }: ScrollFadeProps) {
  return (
    <div className={cn('relative', className)}>
      <div className="pointer-events-none absolute inset-y-0 left-0 z-10 w-6 scroll-fade-left" />
      <div className="pointer-events-none absolute inset-y-0 right-0 z-10 w-6 scroll-fade-right" />
      <div className="overflow-x-auto">{children}</div>
    </div>
  )
}
