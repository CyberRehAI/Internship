import type { ReactNode } from 'react'
import { cn } from '../../lib/cn'

type PanelProps = {
  children: ReactNode
  className?: string
  title?: string
  action?: ReactNode
}

export function Panel({ children, className, title, action }: PanelProps) {
  return (
    <section className={cn('panel-surface rounded-[3px]', className)}>
      {(title || action) && (
        <header className="flex items-center justify-between border-b border-line px-4 py-3">
          {title && <h2 className="text-xs font-semibold uppercase tracking-widest text-neutral-400">{title}</h2>}
          {action}
        </header>
      )}
      <div className="p-4">{children}</div>
    </section>
  )
}
