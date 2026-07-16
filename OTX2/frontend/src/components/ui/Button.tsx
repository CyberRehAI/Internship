import type { ButtonHTMLAttributes, ReactNode } from 'react'
import { cn } from '../../lib/cn'

type ButtonVariant = 'primary' | 'ghost' | 'danger' | 'secondary'

type ButtonProps = ButtonHTMLAttributes<HTMLButtonElement> & {
  variant?: ButtonVariant
  children: ReactNode
  mono?: boolean
}

const variantClasses: Record<ButtonVariant, string> = {
  primary: 'border border-accent bg-accent/10 text-accent hover:bg-accent/20 hover:shadow-[0_0_15px_rgba(255,122,0,0.15)]',
  ghost: 'border border-line bg-transparent text-neutral-400 hover:bg-surface-2 hover:text-[#F5F5F5]',
  danger: 'border border-danger/40 bg-danger/10 text-danger hover:bg-danger/20',
  secondary: 'border border-line bg-surface-2 text-neutral-300 hover:bg-[#252525] hover:text-[#F5F5F5]',
}

export function Button({
  variant = 'primary',
  children,
  className,
  mono = false,
  type = 'button',
  ...props
}: ButtonProps) {
  return (
    <button
      type={type}
      className={cn(
        'inline-flex items-center justify-center gap-2 px-3 py-2 text-xs font-semibold uppercase tracking-wide transition-all duration-150 ease-out',
        mono ? 'font-data' : 'font-sans',
        variantClasses[variant],
        'rounded-[3px]',
        className,
      )}
      {...props}
    >
      {children}
    </button>
  )
}
