import { useCallback, useMemo } from 'react'
import { useLocalStorage } from './useLocalStorage'

export type SearchLogEntry = {
  query: string
  detectedType?: string
  timestamp: string
}

export type ExportLogEntry = {
  exportId: string
  filename: string
  format: string
  mode: string
  iocCount: number
  timestamp: string
}

export type PulseViewEntry = {
  pulseId: string
  pulseName: string
  timestamp: string
}

export type ActivityEvent = {
  id: string
  type: 'search' | 'export' | 'pulse_view'
  label: string
  timestamp: string
}

function bucketByDay(entries: SearchLogEntry[]) {
  const buckets: Record<string, number> = {}
  for (const entry of entries) {
    const day = entry.timestamp.slice(0, 10)
    buckets[day] = (buckets[day] ?? 0) + 1
  }
  return Object.entries(buckets)
    .sort(([a], [b]) => a.localeCompare(b))
    .map(([date, count]) => ({ date, count }))
}

export function useTelemetry() {
  const [recentSearches] = useLocalStorage<SearchLogEntry[]>('otx_recent_searches', [])
  const [exportHistory] = useLocalStorage<ExportLogEntry[]>('otx_export_history', [])
  const [lastDumpStats] = useLocalStorage<Record<string, number>>('otx_last_dump_stats', {})
  const [pulsesViewed, setPulsesViewed] = useLocalStorage<PulseViewEntry[]>('otx_pulses_viewed', [])

  const totalSearches = recentSearches.length
  const exportedIocs = exportHistory.reduce((sum, item) => sum + item.iocCount, 0)
  const pulsesViewedCount = pulsesViewed.length

  const iocTypeDistribution = useMemo(
    () => Object.entries(lastDumpStats).map(([name, value]) => ({ name, value })),
    [lastDumpStats],
  )

  const searchesPerDay = useMemo(() => bucketByDay(recentSearches), [recentSearches])

  const activityTimeline = useMemo<ActivityEvent[]>(() => {
    const events: ActivityEvent[] = [
      ...recentSearches.map((item) => ({
        id: `search-${item.timestamp}-${item.query}`,
        type: 'search' as const,
        label: `Query executed: ${item.query}`,
        timestamp: item.timestamp,
      })),
      ...exportHistory.map((item) => ({
        id: `export-${item.exportId}`,
        type: 'export' as const,
        label: `Export generated: ${item.filename}`,
        timestamp: item.timestamp,
      })),
      ...pulsesViewed.map((item) => ({
        id: `pulse-${item.pulseId}-${item.timestamp}`,
        type: 'pulse_view' as const,
        label: `Pulse viewed: ${item.pulseName}`,
        timestamp: item.timestamp,
      })),
    ]
    return events.sort((a, b) => b.timestamp.localeCompare(a.timestamp)).slice(0, 20)
  }, [recentSearches, exportHistory, pulsesViewed])

  const logPulseView = useCallback((pulseId: string, pulseName: string) => {
    setPulsesViewed((prev) =>
      [{ pulseId, pulseName, timestamp: new Date().toISOString() }, ...prev]
        .slice(0, 50)
        .filter((item, idx, arr) => arr.findIndex((inner) => inner.pulseId === item.pulseId) === idx),
    )
  }, [setPulsesViewed])

  return {
    recentSearches,
    exportHistory,
    lastDumpStats,
    pulsesViewed,
    totalSearches,
    exportedIocs,
    pulsesViewedCount,
    iocTypeDistribution,
    searchesPerDay,
    activityTimeline,
    logPulseView,
  }
}
