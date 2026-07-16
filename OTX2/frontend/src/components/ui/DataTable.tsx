import type { ReactNode } from 'react'
import { ScrollFade } from './ScrollFade'
import { cn } from '../../lib/cn'

export type Column<T> = {
  key: string
  header: string
  render: (row: T) => ReactNode
  mono?: boolean
  className?: string
}

type DataTableProps<T> = {
  columns: Column<T>[]
  rows: T[]
  rowKey: (row: T, index: number) => string
  emptyMessage?: string
}

export function DataTable<T>({ columns, rows, rowKey, emptyMessage = 'Awaiting telemetry' }: DataTableProps<T>) {
  if (rows.length === 0) {
    return <p className="text-sm text-neutral-500">{emptyMessage}</p>
  }

  return (
    <ScrollFade>
      <table className="min-w-full border-collapse text-left text-xs">
        <thead className="sticky top-0 z-20 bg-surface-1">
          <tr className="border-b border-line">
            {columns.map((col) => (
              <th
                key={col.key}
                className={cn(
                  'px-3 py-2 text-[10px] font-semibold uppercase tracking-widest text-neutral-500',
                  col.className,
                )}
              >
                {col.header}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((row, index) => (
            <tr key={rowKey(row, index)} className="row-hover border-b border-line/60">
              {columns.map((col) => (
                <td
                  key={col.key}
                  className={cn('px-3 py-2 text-neutral-300', col.mono && 'font-data text-neutral-200', col.className)}
                >
                  {col.render(row)}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </ScrollFade>
  )
}
