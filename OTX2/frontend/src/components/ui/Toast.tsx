import { useCallback, useMemo, useState, type ReactNode } from 'react'
import { AnimatePresence, motion } from 'framer-motion'
import { X } from 'lucide-react'
import { Button } from './Button'
import { cn } from '../../lib/cn'
import { ToastContext } from './toast-context'

type ToastItem = {
  id: string
  message: string
  variant: 'success' | 'error'
}

export function ToastProvider({ children }: { children: ReactNode }) {
  const [items, setItems] = useState<ToastItem[]>([])

  const push = useCallback((message: string, variant: 'success' | 'error' = 'success') => {
    const id = crypto.randomUUID()
    setItems((prev) => [...prev, { id, message, variant }])
    window.setTimeout(() => {
      setItems((prev) => prev.filter((item) => item.id !== id))
    }, 4000)
  }, [])

  const dismiss = useCallback((id: string) => {
    setItems((prev) => prev.filter((item) => item.id !== id))
  }, [])

  const value = useMemo(() => ({ push }), [push])

  return (
    <ToastContext.Provider value={value}>
      {children}
      <div className="pointer-events-none fixed bottom-4 right-4 z-50 flex w-full max-w-sm flex-col gap-2">
        <AnimatePresence>
          {items.map((item) => (
            <motion.div
              key={item.id}
              initial={{ opacity: 0, y: 8 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: 8 }}
              transition={{ duration: 0.15, ease: 'easeOut' }}
              className={cn(
                'pointer-events-auto panel-surface flex items-start justify-between gap-3 p-3 text-sm text-neutral-200',
                item.variant === 'success' ? 'border-success/40' : 'border-danger/40',
              )}
              role="status"
            >
              <span>{item.message}</span>
              <Button
                variant="ghost"
                aria-label="Dismiss notification"
                className="!px-1 !py-1"
                onClick={() => dismiss(item.id)}
              >
                <X className="h-3.5 w-3.5" />
              </Button>
            </motion.div>
          ))}
        </AnimatePresence>
      </div>
    </ToastContext.Provider>
  )
}
