import { useMemo, useState } from 'react'
import { ExternalLink, Eye } from 'lucide-react'
import { Badge, TlpBadge } from './ui/Badge'
import { CopyButton } from './ui/CopyButton'
import { IocTypeBadge } from './ui/IocTypeBadge'
import { Modal } from './ui/Modal'
import { Panel } from './ui/Panel'
import { ScrollFade } from './ui/ScrollFade'
import { Tooltip } from './ui/Tooltip'
import { FILTER_LABELS, getIocTypeMeta, otxIndicatorUrl, type IocCategory } from '../lib/iocTypes'
import { cn } from '../lib/cn'
import type { IOCRecord, PulseIntelligenceContext } from '../types/otx'

type IocPreviewProps = {
  iocs: IOCRecord[]
  pulsesProcessed: number
  pulseContexts: PulseIntelligenceContext[]
}

function truncateMiddle(value: string, max = 44): string {
  if (value.length <= max) return value
  const head = Math.ceil(max / 2) - 2
  const tail = Math.floor(max / 2) - 2
  return `${value.slice(0, head)}…${value.slice(value.length - tail)}`
}

export function IocPreview({ iocs, pulsesProcessed, pulseContexts }: IocPreviewProps) {
  const [activeFilter, setActiveFilter] = useState<IocCategory | 'all'>('all')
  const [detail, setDetail] = useState<IOCRecord | null>(null)

  const countsByCategory = useMemo(() => {
    const counts: Record<string, number> = {}
    for (const ioc of iocs) {
      const { category } = getIocTypeMeta(ioc.type)
      counts[category] = (counts[category] ?? 0) + 1
    }
    return counts
  }, [iocs])

  const filteredIocs = useMemo(() => {
    if (activeFilter === 'all') return iocs
    return iocs.filter((ioc) => getIocTypeMeta(ioc.type).category === activeFilter)
  }, [iocs, activeFilter])

  // Single-pulse dumps: surface pulse context once instead of a repeated column.
  const singlePulse = useMemo(() => {
    const ids = new Set(iocs.map((ioc) => ioc.pulse_id).filter(Boolean))
    if (ids.size === 1) return iocs[0]
    return null
  }, [iocs])

  return (
    <div className="space-y-4">
      {singlePulse && (
        <Panel title="Source Pulse">
          <div className="space-y-2">
            <div className="flex flex-wrap items-center gap-2">
              <h3 className="text-sm font-semibold text-[#F5F5F5]">{singlePulse.pulse_name || 'Unnamed pulse'}</h3>
              {singlePulse.tlp && <TlpBadge value={singlePulse.tlp} />}
            </div>
            <div className="flex flex-wrap gap-3 text-xs text-neutral-400">
              {singlePulse.author && (
                <span>
                  Author: <span className="font-data text-neutral-200">{singlePulse.author}</span>
                </span>
              )}
              {singlePulse.created && (
                <span>
                  Created: <span className="font-data text-neutral-200">{singlePulse.created}</span>
                </span>
              )}
              {singlePulse.pulse_id && (
                <span className="inline-flex items-center gap-1">
                  ID: <span className="font-data text-neutral-200">{singlePulse.pulse_id}</span>
                  <CopyButton value={singlePulse.pulse_id} label="Copy pulse ID" />
                </span>
              )}
            </div>
            {singlePulse.tags?.length > 0 && (
              <div className="flex flex-wrap gap-2">
                {singlePulse.tags.slice(0, 10).map((tag) => (
                  <Badge key={tag}>{tag}</Badge>
                ))}
              </div>
            )}
          </div>
        </Panel>
      )}

      {pulseContexts.length > 0 && (
        <Panel title={`Pulse Intelligence Context (${pulseContexts.length})`}>
          <div className="grid gap-3 lg:grid-cols-2">
            {pulseContexts.map((context) => (
              <article key={context.pulse_id} className="row-hover border border-line bg-surface-2 p-3">
                <p className="text-[10px] font-semibold uppercase tracking-widest text-neutral-500">Immediate Threat</p>
                <h4 className="mt-1 text-sm font-semibold text-[#F5F5F5]">{context.immediate_threat}</h4>
                {context.threat_summary ? (
                  <p className="mt-2 text-xs text-neutral-400">{context.threat_summary}</p>
                ) : (
                  <p className="mt-2 text-xs text-neutral-500">No threat summary provided.</p>
                )}

                <div className="mt-3 flex flex-wrap items-center gap-2">
                  {context.tlp && <TlpBadge value={context.tlp} />}
                  {context.author && <Badge>{`Author: ${context.author}`}</Badge>}
                  {context.created && <Badge>{`Created: ${context.created}`}</Badge>}
                </div>

                <div className="mt-3 space-y-2">
                  <ContextRow label="Adversary" value={context.adversary || 'Unclassified'} />
                  <ContextRow
                    label="Targeted Country"
                    value={context.targeted_countries.length > 0 ? context.targeted_countries.join(', ') : 'Unknown'}
                  />
                  <ContextRow
                    label="Malware Family"
                    value={context.malware_families.length > 0 ? context.malware_families.join(', ') : 'Not specified'}
                  />
                </div>

                {context.attack_ids.length > 0 && (
                  <div className="mt-3">
                    <p className="text-[10px] font-semibold uppercase tracking-widest text-neutral-500">MITRE ATT&CK</p>
                    <div className="mt-1 flex flex-wrap gap-2">
                      {context.attack_ids.map((id) => (
                        <Badge key={id}>{id}</Badge>
                      ))}
                    </div>
                  </div>
                )}

                {context.tags.length > 0 && (
                  <div className="mt-3">
                    <p className="text-[10px] font-semibold uppercase tracking-widest text-neutral-500">Tags</p>
                    <div className="mt-1 flex flex-wrap gap-2">
                      {context.tags.map((tag) => (
                        <Badge key={`${context.pulse_id}-${tag}`}>{tag}</Badge>
                      ))}
                    </div>
                  </div>
                )}

                {context.references.length > 0 && (
                  <div className="mt-3">
                    <p className="text-[10px] font-semibold uppercase tracking-widest text-neutral-500">References</p>
                    <ul className="mt-1 space-y-1">
                      {context.references.slice(0, 3).map((ref) => (
                        <li key={`${context.pulse_id}-${ref}`} className="truncate font-data text-[10px] text-accent">
                          {ref}
                        </li>
                      ))}
                    </ul>
                  </div>
                )}
              </article>
            ))}
          </div>
        </Panel>
      )}

      <section className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
        <div className="panel-surface p-4">
          <p className="text-[10px] font-semibold uppercase tracking-widest text-neutral-500">Total IOCs</p>
          <p className="mt-2 font-data text-2xl font-semibold text-accent">{iocs.length}</p>
          <p className="mt-1 text-xs text-neutral-500">
            Across <span className="font-data text-neutral-300">{pulsesProcessed}</span> pulse(s)
          </p>
        </div>
        {FILTER_LABELS.filter((f) => f.id !== 'all').map((filter) => (
          <div key={filter.id} className="panel-surface p-4">
            <p className="text-[10px] font-semibold uppercase tracking-widest text-neutral-500">{filter.label}</p>
            <p className="mt-2 font-data text-2xl font-semibold text-neutral-200">{countsByCategory[filter.id] ?? 0}</p>
          </div>
        ))}
      </section>

      <Panel title={`Indicators (${filteredIocs.length})`}>
        <div className="mb-4 flex flex-wrap gap-2">
          {FILTER_LABELS.map((filter) => {
            const count = filter.id === 'all' ? iocs.length : countsByCategory[filter.id] ?? 0
            return (
              <button
                key={filter.id}
                type="button"
                onClick={() => setActiveFilter(filter.id)}
                className={cn(
                  'inline-flex items-center gap-2 border px-3 py-1 text-xs font-semibold uppercase tracking-wide transition-colors duration-150 ease-out',
                  'rounded-[2px]',
                  activeFilter === filter.id
                    ? 'border-accent bg-accent/10 text-accent'
                    : 'border-line bg-surface-2 text-neutral-400 hover:text-neutral-200',
                )}
              >
                {filter.label}
                <span className="font-data text-[10px] opacity-70">{count}</span>
              </button>
            )
          })}
        </div>

        {filteredIocs.length === 0 ? (
          <p className="text-sm text-neutral-500">No indicators match this filter.</p>
        ) : (
          <ScrollFade>
            <table className="min-w-full border-collapse text-left text-xs">
              <thead className="sticky top-0 z-20 bg-surface-1">
                <tr className="border-b border-line">
                  <th className="px-3 py-2 text-[10px] font-semibold uppercase tracking-widest text-neutral-500">Type</th>
                  <th className="px-3 py-2 text-[10px] font-semibold uppercase tracking-widest text-neutral-500">Indicator</th>
                  <th className="px-3 py-2 text-[10px] font-semibold uppercase tracking-widest text-neutral-500">Description</th>
                  <th className="px-3 py-2 text-right text-[10px] font-semibold uppercase tracking-widest text-neutral-500">Actions</th>
                </tr>
              </thead>
              <tbody>
                {filteredIocs.map((ioc, index) => (
                  <tr key={`${ioc.type}-${ioc.value}-${index}`} className="row-hover border-b border-line/60">
                    <td className="px-3 py-2 align-top">
                      <IocTypeBadge type={ioc.type} />
                    </td>
                    <td className="px-3 py-2 align-top">
                      <div className="flex items-center gap-2">
                        <Tooltip label={ioc.value}>
                          <span className="font-data text-neutral-200">{truncateMiddle(ioc.value)}</span>
                        </Tooltip>
                        <CopyButton value={ioc.value} label="Copy indicator" />
                      </div>
                    </td>
                    <td className="px-3 py-2 align-top">
                      {ioc.description ? (
                        <span className="text-neutral-400">{ioc.description}</span>
                      ) : (
                        <span className="inline-flex items-center border border-line bg-surface-2 px-2 py-0.5 text-[10px] uppercase tracking-wider text-neutral-600 rounded-[2px]">
                          No Description
                        </span>
                      )}
                    </td>
                    <td className="px-3 py-2 align-top">
                      <div className="flex items-center justify-end gap-1">
                        {ioc.related_pulse_count > 1 && (
                          <Tooltip
                            label={ioc.related_pulses
                              .map((pulse) => `${pulse.pulse_name || 'Unnamed pulse'} (${pulse.pulse_id})`)
                              .join('\n')}
                          >
                            <span className="inline-flex items-center border border-line bg-surface-2 px-2 py-0.5 font-data text-[10px] text-neutral-300 rounded-[2px]">
                              {ioc.related_pulse_count} pulses
                            </span>
                          </Tooltip>
                        )}
                        <button
                          type="button"
                          aria-label="View indicator details"
                          onClick={() => setDetail(ioc)}
                          className="inline-flex items-center justify-center border border-line bg-surface-2 p-1 text-neutral-400 transition-colors duration-150 ease-out hover:text-accent rounded-[2px]"
                        >
                          <Eye className="h-3 w-3" />
                        </button>
                        <a
                          href={otxIndicatorUrl(ioc.type, ioc.value)}
                          target="_blank"
                          rel="noreferrer"
                          aria-label="Search indicator in OTX"
                          className="inline-flex items-center justify-center border border-line bg-surface-2 p-1 text-neutral-400 transition-colors duration-150 ease-out hover:text-accent rounded-[2px]"
                        >
                          <ExternalLink className="h-3 w-3" />
                        </a>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </ScrollFade>
        )}
      </Panel>

      <Modal open={detail !== null} onClose={() => setDetail(null)} title="Indicator Detail">
        {detail && (
          <div className="space-y-3 text-sm">
            <div className="flex flex-wrap items-center gap-2">
              <IocTypeBadge type={detail.type} />
              {detail.tlp && <TlpBadge value={detail.tlp} />}
            </div>
            <DetailRow label="Indicator" value={detail.value} copy />
            <DetailRow label="Description" value={detail.description || 'No Description'} />
            <DetailRow label="Pulse" value={detail.pulse_name || '—'} />
            <DetailRow label="Author" value={detail.author || '—'} />
            <DetailRow label="Created" value={detail.created || '—'} />
            {detail.tags?.length > 0 && (
              <div>
                <p className="text-[10px] font-semibold uppercase tracking-widest text-neutral-500">Tags</p>
                <div className="mt-1 flex flex-wrap gap-2">
                  {detail.tags.map((tag) => (
                    <Badge key={tag}>{tag}</Badge>
                  ))}
                </div>
              </div>
            )}
            {detail.attack_ids?.length > 0 && (
              <div>
                <p className="text-[10px] font-semibold uppercase tracking-widest text-neutral-500">MITRE ATT&CK</p>
                <div className="mt-1 flex flex-wrap gap-2">
                  {detail.attack_ids.map((id) => (
                    <Badge key={id}>{id}</Badge>
                  ))}
                </div>
              </div>
            )}
            {detail.related_pulse_count > 0 && (
              <div>
                <p className="text-[10px] font-semibold uppercase tracking-widest text-neutral-500">Related Pulses</p>
                <ul className="mt-1 space-y-1">
                  {detail.related_pulses.map((pulse) => (
                    <li key={`${pulse.pulse_id}-${pulse.pulse_name || 'pulse'}`} className="font-data text-[10px] text-neutral-300">
                      {pulse.pulse_name || 'Unnamed pulse'} ({pulse.pulse_id})
                    </li>
                  ))}
                </ul>
              </div>
            )}
            <a
              href={otxIndicatorUrl(detail.type, detail.value)}
              target="_blank"
              rel="noreferrer"
              className="inline-flex items-center gap-2 border border-accent bg-accent/10 px-3 py-2 text-xs font-semibold uppercase tracking-wide text-accent rounded-[2px]"
            >
              <ExternalLink className="h-3.5 w-3.5" />
              Open in OTX
            </a>
          </div>
        )}
      </Modal>
    </div>
  )
}

function ContextRow({ label, value }: { label: string; value: string }) {
  return (
    <p className="text-xs text-neutral-400">
      <span className="text-neutral-500">{label}:</span>{' '}
      <span className="font-data text-neutral-200">{value}</span>
    </p>
  )
}

function DetailRow({ label, value, copy = false }: { label: string; value: string; copy?: boolean }) {
  return (
    <div>
      <p className="text-[10px] font-semibold uppercase tracking-widest text-neutral-500">{label}</p>
      <div className="mt-1 flex items-start gap-2">
        <span className="break-all font-data text-neutral-200">{value}</span>
        {copy && <CopyButton value={value} />}
      </div>
    </div>
  )
}
