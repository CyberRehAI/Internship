import { useQuery } from '@tanstack/react-query'
import { Area, AreaChart, Bar, BarChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import { getHealth } from '../api/client'
import { Badge } from '../components/ui/Badge'
import { EmptyState } from '../components/ui/EmptyState'
import { Panel } from '../components/ui/Panel'
import { PulsingDot } from '../components/ui/PulsingDot'
import { StatCard } from '../components/ui/StatCard'
import { useTelemetry } from '../hooks/useTelemetry'
import { useRelativeTime } from '../hooks/useRelativeTime'

const chartAxis = { stroke: '#525252', fontSize: 10 }
const chartTooltip = {
  contentStyle: { background: '#131313', border: '1px solid #2A2A2A', borderRadius: '3px' },
  labelStyle: { color: '#A3A3A3' },
}

export function DashboardPage() {
  const {
    totalSearches,
    exportedIocs,
    pulsesViewedCount,
    iocTypeDistribution,
    searchesPerDay,
    activityTimeline,
    recentSearches,
    exportHistory,
  } = useTelemetry()

  const { data: health, isLoading, isError, dataUpdatedAt } = useQuery({
    queryKey: ['health'],
    queryFn: getHealth,
    refetchInterval: 30000,
  })

  const lastSync = useRelativeTime(dataUpdatedAt || undefined)
  const apiStatus = isLoading ? 'Checking' : isError ? 'Offline' : 'Live'

  return (
    <div className="space-y-6">
      <header className="flex flex-wrap items-center justify-between gap-4">
        <div>
          <p className="text-[10px] font-semibold uppercase tracking-widest text-neutral-500">Command Surface</p>
          <h1 className="mt-1 text-2xl font-semibold text-[#F5F5F5]">Threat Operations Overview</h1>
        </div>
        <div className="flex flex-wrap items-center gap-4 text-xs text-neutral-400">
          <div className="flex items-center gap-2">
            <PulsingDot status={isError ? 'error' : isLoading ? 'loading' : 'connected'} />
            <span>{apiStatus} ingest</span>
          </div>
          <span className="font-data text-neutral-300">{health?.otx_user ? `Analyst: ${health.otx_user}` : 'Analyst: —'}</span>
          <span className="font-data">{lastSync}</span>
        </div>
      </header>

      <section className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
        <StatCard label="Total Searches" value={totalSearches} caption="Session query count" />
        <StatCard label="Exported IOCs" value={exportedIocs} caption="Cumulative export volume" />
        <StatCard label="Pulses Viewed" value={pulsesViewedCount} caption="Unique pulse inspections" />
        <StatCard label="API Status" value={apiStatus} caption={health?.latency_ms ? `${health.latency_ms}ms latency` : 'Awaiting telemetry'} />
      </section>

      <section className="grid gap-4 xl:grid-cols-3">
        <Panel title="IOC Type Distribution" className="xl:col-span-1">
          {iocTypeDistribution.length === 0 ? (
            <EmptyState title="Awaiting telemetry" description="Run an IOC dump to populate distribution." />
          ) : (
            <div className="h-56">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={iocTypeDistribution}>
                  <XAxis dataKey="name" {...chartAxis} />
                  <YAxis {...chartAxis} />
                  <Tooltip {...chartTooltip} />
                  <Bar dataKey="value" fill="#FF7A00" radius={[2, 2, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            </div>
          )}
        </Panel>

        <Panel title="Searches Per Day" className="xl:col-span-1">
          {searchesPerDay.length === 0 ? (
            <EmptyState title="Awaiting telemetry" description="Execute a global search to begin tracking." />
          ) : (
            <div className="h-56">
              <ResponsiveContainer width="100%" height="100%">
                <AreaChart data={searchesPerDay}>
                  <XAxis dataKey="date" {...chartAxis} />
                  <YAxis {...chartAxis} />
                  <Tooltip {...chartTooltip} />
                  <Area type="monotone" dataKey="count" stroke="#FF7A00" fill="rgba(255,122,0,0.2)" />
                </AreaChart>
              </ResponsiveContainer>
            </div>
          )}
        </Panel>

        <Panel title="Recent Activity Timeline" className="xl:col-span-1">
          {activityTimeline.length === 0 ? (
            <EmptyState title="Awaiting telemetry" />
          ) : (
            <ul className="max-h-56 space-y-2 overflow-y-auto">
              {activityTimeline.map((event) => (
                <li key={event.id} className="row-hover border border-line bg-surface-2 px-3 py-2">
                  <p className="text-xs text-neutral-300">{event.label}</p>
                  <p className="mt-1 font-data text-[10px] text-neutral-500">{event.timestamp}</p>
                </li>
              ))}
            </ul>
          )}
        </Panel>
      </section>

      <section className="grid gap-4 lg:grid-cols-2">
        <Panel title="Recent Searches">
          {recentSearches.length === 0 ? (
            <EmptyState title="No queries logged" />
          ) : (
            <ul className="space-y-2">
              {recentSearches.slice(0, 8).map((item) => (
                <li key={`${item.timestamp}-${item.query}`} className="row-hover border border-line bg-surface-2 px-3 py-2">
                  <div className="flex items-center justify-between gap-2">
                    <span className="font-data text-sm text-accent">{item.query}</span>
                    {item.detectedType && <Badge>{item.detectedType}</Badge>}
                  </div>
                  <p className="mt-1 font-data text-[10px] text-neutral-500">{item.timestamp}</p>
                </li>
              ))}
            </ul>
          )}
        </Panel>

        <Panel title="Recent Exports">
          {exportHistory.length === 0 ? (
            <EmptyState title="No exports generated" />
          ) : (
            <ul className="space-y-2">
              {exportHistory.slice(0, 8).map((item) => (
                <li key={item.exportId} className="row-hover border border-line bg-surface-2 px-3 py-2">
                  <div className="flex flex-wrap items-center justify-between gap-2">
                    <span className="font-data text-sm text-neutral-200">{item.filename}</span>
                    <div className="flex gap-2">
                      <Badge>{item.format}</Badge>
                      <Badge>{item.mode}</Badge>
                    </div>
                  </div>
                  <p className="mt-1 text-xs text-neutral-500">
                    IOC count: <span className="font-data text-neutral-300">{item.iocCount}</span>
                  </p>
                </li>
              ))}
            </ul>
          )}
        </Panel>
      </section>
    </div>
  )
}
