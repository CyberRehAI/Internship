import { useQuery } from '@tanstack/react-query'
import { Copy, ExternalLink } from 'lucide-react'
import { useEffect, useMemo, useState } from 'react'
import { useSearchParams } from 'react-router-dom'
import { getPulseDetails, getPulseIndicators, searchPulses } from '../api/client'
import { Badge, TlpBadge } from '../components/ui/Badge'
import { Button } from '../components/ui/Button'
import { CopyButton } from '../components/ui/CopyButton'
import { DataTable } from '../components/ui/DataTable'
import { EmptyState } from '../components/ui/EmptyState'
import { IocTypeBadge } from '../components/ui/IocTypeBadge'
import { Panel } from '../components/ui/Panel'
import { SkeletonCard } from '../components/ui/Skeleton'
import { Tooltip } from '../components/ui/Tooltip'
import { useTelemetry } from '../hooks/useTelemetry'
import { otxIndicatorUrl } from '../lib/iocTypes'
import type { Pulse } from '../types/otx'

type IndicatorRow = {
  type: string
  value: string
  description: string
  relatedPulses: number
  references: string[]
}

const PAGE_SIZE = 15

export function PulseViewerPage() {
  const [searchParams, setSearchParams] = useSearchParams()
  const selectedId = searchParams.get('id')
  const [query, setQuery] = useState('ransomware')
  const [indicatorFilter, setIndicatorFilter] = useState('')
  const [page, setPage] = useState(1)
  const { logPulseView } = useTelemetry()

  const listQuery = useQuery({
    queryKey: ['pulse-search', query],
    queryFn: () => searchPulses(query),
    enabled: !selectedId,
  })

  const detailQuery = useQuery({
    queryKey: ['pulse-detail', selectedId],
    queryFn: () => getPulseDetails(selectedId!),
    enabled: Boolean(selectedId),
  })

  const indicatorsQuery = useQuery({
    queryKey: ['pulse-indicators', selectedId],
    queryFn: () => getPulseIndicators(selectedId!),
    enabled: Boolean(selectedId),
  })

  useEffect(() => {
    if (detailQuery.data) {
      logPulseView(detailQuery.data.id, detailQuery.data.name)
    }
  }, [detailQuery.data, logPulseView])

  const indicators = useMemo<IndicatorRow[]>(() => {
    return (indicatorsQuery.data?.results ?? []).map((item) => ({
      type: String(item.type ?? 'unknown'),
      value: String(item.indicator ?? ''),
      description: String(item.description ?? '—'),
      relatedPulses: Number(item.related_pulse_count ?? item.pulse_count ?? item.pulses_count ?? 0),
      references: Array.isArray(item.references) ? (item.references as string[]) : [],
    }))
  }, [indicatorsQuery.data])

  const filteredIndicators = useMemo(() => {
    const term = indicatorFilter.trim().toLowerCase()
    if (!term) return indicators
    return indicators.filter(
      (row) =>
        row.value.toLowerCase().includes(term) ||
        row.type.toLowerCase().includes(term) ||
        row.description.toLowerCase().includes(term),
    )
  }, [indicators, indicatorFilter])

  const totalPages = Math.max(1, Math.ceil(filteredIndicators.length / PAGE_SIZE))
  const pagedIndicators = filteredIndicators.slice((page - 1) * PAGE_SIZE, page * PAGE_SIZE)

  const openPulse = (pulse: Pulse) => {
    setSearchParams({ id: pulse.id })
    setPage(1)
  }

  const backToList = () => {
    setSearchParams({})
    setPage(1)
  }

  if (selectedId) {
    const pulse = detailQuery.data
    return (
      <div className="space-y-6">
        <header className="flex flex-wrap items-center justify-between gap-3">
          <div>
            <p className="text-[10px] font-semibold uppercase tracking-widest text-neutral-500">Pulse Detail</p>
            <h1 className="mt-1 text-2xl font-semibold">{pulse?.name || 'Loading pulse...'}</h1>
          </div>
          <Button variant="ghost" onClick={backToList}>
            Back to list
          </Button>
        </header>

        {detailQuery.isLoading && <SkeletonCard />}

        {pulse && (
          <Panel title="Pulse Metadata">
            <div className="space-y-3 text-sm">
              <div>
                <p className="text-[10px] font-semibold uppercase tracking-widest text-neutral-500">Immediate Threat</p>
                <h2 className="mt-1 text-lg font-semibold text-[#F5F5F5]">{pulse.name || 'Pulse threat observed'}</h2>
              </div>
              <div className="flex flex-wrap gap-3 text-xs text-neutral-400">
                <span>
                  Author: <span className="font-data text-neutral-200">{pulse.author_name || '—'}</span>
                </span>
                <span>
                  Created: <span className="font-data text-neutral-200">{pulse.created || '—'}</span>
                </span>
                <span>
                  Modified: <span className="font-data text-neutral-200">{pulse.modified || '—'}</span>
                </span>
                <span>
                  Visibility: <span className="font-data text-neutral-200">{pulse.visibility || 'Public'}</span>
                </span>
                <TlpBadge value={pulse.TLP} />
              </div>
              <p className="text-neutral-300">{pulse.description || 'No description provided.'}</p>
              <div className="space-y-2 text-xs text-neutral-400">
                <ContextRow label="Adversary" value={pulse.adversary || 'Unclassified'} />
                <ContextRow
                  label="Targeted Country"
                  value={pulse.targeted_countries?.length ? pulse.targeted_countries.join(', ') : 'Unknown'}
                />
                <ContextRow
                  label="Malware Family"
                  value={pulse.malware_families?.length ? pulse.malware_families.join(', ') : 'Unknown'}
                />
              </div>
              <div className="flex flex-wrap gap-2">
                {pulse.attack_ids?.map((id) => (
                  <Badge key={id}>{id}</Badge>
                ))}
                {pulse.tags?.map((tag) => (
                  <Badge key={tag}>{tag}</Badge>
                ))}
              </div>
              {pulse.references?.length > 0 && (
                <div className="space-y-1">
                  <p className="text-[10px] font-semibold uppercase tracking-widest text-neutral-500">References</p>
                  <ul className="space-y-1">
                    {pulse.references.map((ref) => (
                      <li key={ref} className="font-data text-xs text-accent">
                        {ref}
                      </li>
                    ))}
                  </ul>
                </div>
              )}
            </div>
          </Panel>
        )}

        <Panel
          title="Indicators"
          action={
            <input
              value={indicatorFilter}
              onChange={(e) => {
                setIndicatorFilter(e.target.value)
                setPage(1)
              }}
              placeholder="Filter indicators"
              className="border border-line bg-surface-0 px-2 py-1 font-data text-xs text-neutral-300"
              aria-label="Filter indicators"
            />
          }
        >
          {indicatorsQuery.isLoading ? (
            <SkeletonCard />
          ) : (
            <>
              <DataTable
                columns={[
                  { key: 'type', header: 'Type', render: (row) => <IocTypeBadge type={row.type} /> },
                  {
                    key: 'value',
                    header: 'Value',
                    render: (row) => (
                      <div className="flex items-center gap-2">
                        <span className="font-data text-neutral-200">{row.value}</span>
                        <CopyButton value={row.value} label="Copy indicator value" />
                      </div>
                    ),
                    mono: true,
                  },
                  {
                    key: 'description',
                    header: 'Description',
                    render: (row) =>
                      row.description && row.description !== '—' ? (
                        row.description
                      ) : (
                        <span className="inline-flex items-center border border-line bg-surface-2 px-2 py-0.5 text-[10px] uppercase tracking-wider text-neutral-600 rounded-[2px]">
                          No Description
                        </span>
                      ),
                  },
                  {
                    key: 'related',
                    header: 'Related Pulses',
                    render: (row) =>
                      row.relatedPulses > 0 ? (
                        <Badge>{`${row.relatedPulses}`}</Badge>
                      ) : (
                        <span className="font-data text-neutral-500">—</span>
                      ),
                    mono: true,
                  },
                  {
                    key: 'actions',
                    header: 'Actions',
                    render: (row) => (
                      <div className="flex items-center gap-1">
                        <CopyButton value={row.value} label="Copy IOC" />
                        <a
                          href={otxIndicatorUrl(row.type, row.value)}
                          target="_blank"
                          rel="noreferrer"
                          aria-label="Search in OTX"
                          className="inline-flex items-center justify-center border border-line bg-surface-2 p-1 text-neutral-400 transition-colors duration-150 ease-out hover:text-accent rounded-[2px]"
                        >
                          <ExternalLink className="h-3 w-3" />
                        </a>
                        {row.references.length > 0 && (
                          <Tooltip label={row.references.join('\n')}>
                            <span className="inline-flex items-center justify-center border border-line bg-surface-2 p-1 text-neutral-400 rounded-[2px]">
                              <Copy className="h-3 w-3" />
                            </span>
                          </Tooltip>
                        )}
                      </div>
                    ),
                  },
                ]}
                rows={pagedIndicators}
                rowKey={(row) => `${row.type}-${row.value}`}
                emptyMessage="Query executed - no indicators"
              />
              <div className="mt-3 flex items-center justify-between text-xs text-neutral-500">
                <span>
                  Page <span className="font-data text-neutral-300">{page}</span> of{' '}
                  <span className="font-data text-neutral-300">{totalPages}</span>
                </span>
                <div className="flex gap-2">
                  <Button variant="ghost" disabled={page <= 1} onClick={() => setPage((p) => p - 1)}>
                    Prev
                  </Button>
                  <Button variant="ghost" disabled={page >= totalPages} onClick={() => setPage((p) => p + 1)}>
                    Next
                  </Button>
                </div>
              </div>
            </>
          )}
        </Panel>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      <header>
        <p className="text-[10px] font-semibold uppercase tracking-widest text-neutral-500">Pulse Recon</p>
        <h1 className="mt-1 text-2xl font-semibold">Pulse Viewer</h1>
      </header>

      <Panel>
        <div className="flex flex-col gap-3 md:flex-row">
          <input
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            className="w-full border border-line bg-surface-0 px-3 py-2 font-data text-sm"
            placeholder="Search pulses"
            aria-label="Search pulses"
          />
          <Button onClick={() => listQuery.refetch()}>Execute Query</Button>
        </div>
      </Panel>

      {listQuery.isLoading && <SkeletonCard />}

      {listQuery.data?.results.length === 0 && <EmptyState title="Query executed - no matches" />}

      <div className="grid gap-3">
        {listQuery.data?.results.map((pulse) => (
          <article key={pulse.id} className="panel-surface row-hover p-4">
            <div className="flex flex-wrap items-start justify-between gap-3">
              <div>
                <h2 className="text-sm font-semibold">{pulse.name}</h2>
                <p className="mt-1 text-xs text-neutral-500">{pulse.description}</p>
                <div className="mt-2 flex flex-wrap gap-2">
                  <TlpBadge value={pulse.TLP} />
                  <Badge>{`${pulse.indicator_count ?? 0} IOCs`}</Badge>
                </div>
              </div>
              <Button variant="secondary" onClick={() => openPulse(pulse)}>
                View
              </Button>
            </div>
          </article>
        ))}
      </div>
    </div>
  )
}

function ContextRow({ label, value }: { label: string; value: string }) {
  return (
    <p>
      <span className="text-neutral-500">{label}:</span> <span className="font-data text-neutral-200">{value}</span>
    </p>
  )
}
