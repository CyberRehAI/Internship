import type { InputHTMLAttributes } from 'react'
import { cn } from '../../lib/cn'

type CheckboxProps = Omit<InputHTMLAttributes<HTMLInputElement>, 'type'> & {
  label: string
}

export function Checkbox({ label, className, id, ...props }: CheckboxProps) {
  const inputId = id || label
  return (
    <label htmlFor={inputId} className={cn('flex cursor-pointer items-center gap-3 text-sm text-neutral-300', className)}>
      <span className="relative flex h-4 w-4 items-center justify-center border border-line bg-surface-0">
        <input id={inputId} type="checkbox" className="peer sr-only" {...props} />
        <span className="hidden h-2 w-2 bg-accent peer-checked:block" />
      </span>
      <span>{label}</span>
    </label>
  )
}
