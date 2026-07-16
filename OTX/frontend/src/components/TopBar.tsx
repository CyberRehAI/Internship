import { useQuery } from '@tanstack/react-query'
import { getHealth } from '../api/client'
import { PulsingDot } from './ui/PulsingDot'
import { useRelativeTime } from '../hooks/useRelativeTime'

export function TopBar() {
  const { data, isLoading, isError, dataUpdatedAt } = useQuery({
    queryKey: ['health'],
    queryFn: getHealth,
    refetchInterval: 30000,
  })

  const lastSync = useRelativeTime(dataUpdatedAt || undefined)
  const status = isLoading ? 'loading' : isError ? 'error' : 'connected'

  return (
    <header className="flex flex-wrap items-center justify-between gap-3 border-b border-line bg-surface-1 px-4 py-3">
      <div>
        <p className="text-[10px] font-semibold uppercase tracking-widest text-neutral-500">Live Ingest</p>
        <p className="text-sm text-neutral-400">OTX telemetry channel active</p>
      </div>
      <div className="flex flex-wrap items-center gap-4 text-xs text-neutral-400">
        <div className="flex items-center gap-2">
          <PulsingDot status={status} />
          <span>{status === 'connected' ? 'API connected' : status === 'loading' ? 'Checking API' : 'API error'}</span>
        </div>
        <span className="font-data text-neutral-300">{data?.otx_user ? `Analyst: ${data.otx_user}` : 'Analyst: —'}</span>
        <span className="font-data">{lastSync}</span>
      </div>
    </header>
  )
}
