import { useEffect, useState } from 'react'

export function useRelativeTime(timestamp?: number) {
  const [label, setLabel] = useState('Awaiting telemetry')

  useEffect(() => {
    if (!timestamp) return

    const update = () => {
      const seconds = Math.max(0, Math.floor((Date.now() - timestamp) / 1000))
      if (seconds < 60) {
        setLabel(`Last sync: ${seconds}s ago`)
      } else {
        const minutes = Math.floor(seconds / 60)
        setLabel(`Last sync: ${minutes}m ago`)
      }
    }

    update()
    const timer = window.setInterval(update, 1000)
    return () => window.clearInterval(timer)
  }, [timestamp])

  return label
}
