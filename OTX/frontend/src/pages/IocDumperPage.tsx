import { useMutation, useQuery } from '@tanstack/react-query'
import { useEffect, useMemo, useState } from 'react'
import { CheckCircle2, Download } from 'lucide-react'
import { dumpIOCs, exportIOCs, searchPulses } from '../api/client'
import { IocPreview } from '../components/IocPreview'
import { Button } from '../components/ui/Button'
import { Checkbox } from '../components/ui/Checkbox'
import { EmptyState } from '../components/ui/EmptyState'
import { Modal } from '../components/ui/Modal'
import { Panel } from '../components/ui/Panel'
import { ProgressBar } from '../components/ui/ProgressBar'
import { SkeletonCard } from '../components/ui/Skeleton'
import { useToast } from '../components/ui/useToast'
import { useLocalStorage } from '../hooks/useLocalStorage'
import type { ExportResponse, IOCDumpResponse, Pulse } from '../types/otx'

type SourceMode = 'pulse' | 'keyword' | 'malware' | 'threat_actor'

const SOURCE_MODES: Array<{ id: SourceMode; label: string }> = [
  { id: 'pulse', label: 'Pulse ID' },
  { id: 'keyword', label: 'Keyword' },
  { id: 'malware', label: 'Malware' },
  { id: 'threat_actor', label: 'Threat Actor' },
]

const FILTER_CHIPS = [
  { id: 'all', label: 'All' },
  { id: 'ip', label: 'IP' },
  { id: 'domains', label: 'Domain' },
  { id: 'urls', label: 'URL' },
  { id: 'file_hashes', label: 'Hash' },
  { id: 'cves', label: 'CVE' },
  { id: 'email_addresses', label: 'Email' },
  { id: 'yara', label: 'YARA' },
]

const PULSE_ID_PATTERN = /^[0-9A-Za-z]{24}$/

export function IocDumperPage() {
  const { push: pushToast } = useToast()
  const [sourceMode, setSourceMode] = useState<SourceMode>('keyword')
  const [pulseIdsInput, setPulseIdsInput] = useState('')
  const [searchQuery, setSearchQuery] = useState('')
  const [typeFilter, setTypeFilter] = useState('all')
  const [selectedPulseIds, setSelectedPulseIds] = useState<string[]>([])
  const [dumped, setDumped] = useState<IOCDumpResponse | null>(null)
  const [progress, setProgress] = useState(0)
  const [exportResult, setExportResult] = useState<ExportResponse | null>(null)

  const [, setExportHistory] = useLocalStorage<
    Array<{ exportId: string; filename: string; format: string; mode: string; iocCount: number; timestamp: string }>
  >('otx_export_history', [])
  const [, setLastDumpStats] = useLocalStorage<Record<string, number>>('otx_last_dump_stats', {})

  const previewQuery = useQuery({
    queryKey: ['dumper-preview', sourceMode, searchQuery],
    queryFn: () => searchPulses(searchQuery, 50),
    enabled: sourceMode !== 'pulse' && searchQuery.trim().length > 2,
  })

  const dumpMutation = useMutation({
    mutationFn: dumpIOCs,
    onSuccess: (response) => {
      setDumped(response)
      setLastDumpStats(response.stats.by_type)
      setProgress(100)
      pushToast(`Dump complete: ${response.stats.total} IOCs ingested`)
    },
    onError: (error) => {
      setProgress(0)
      const timedOut =
        typeof error === 'object' && error !== null && 'code' in error && (error as { code?: string }).code === 'ECONNABORTED'
      pushToast(
        timedOut
          ? 'Dump timed out. Narrow the query or select fewer pulses.'
          : 'Dump failed. Verify query parameters.',
        'error',
      )
    },
  })

  const exportMutation = useMutation({
    mutationFn: exportIOCs,
    onSuccess: (result) => {
      setExportHistory((prev) =>
        [
          {
            exportId: result.export_id,
            filename: result.filename,
            format: result.format,
            mode: result.mode,
            iocCount: result.ioc_count,
            timestamp: new Date().toISOString(),
          },
          ...prev,
        ].slice(0, 50),
      )
      setExportResult(result)
      pushToast(`Export ready: ${result.ioc_count} IOCs → ${result.filename}`)
    },
    onError: () => pushToast('Export failed.', 'error'),
  })

  useEffect(() => {
    if (!dumpMutation.isPending) return
    setProgress(8)
    const timer = window.setInterval(() => {
      setProgress((value) => (value >= 92 ? value : value + 7))
    }, 180)
    return () => window.clearInterval(timer)
  }, [dumpMutation.isPending])

  const resolvedPulseIds = useMemo(() => {
    const manual = pulseIdsInput
      .split(/[,\n]/)
      .map((item) => item.trim())
      .filter(Boolean)
    if (sourceMode === 'pulse') return manual
    return selectedPulseIds
  }, [pulseIdsInput, selectedPulseIds, sourceMode])

  const togglePulse = (pulseId: string) => {
    setSelectedPulseIds((prev) =>
      prev.includes(pulseId) ? prev.filter((id) => id !== pulseId) : [...prev, pulseId],
    )
  }

  const triggerDump = () => {
    const invalidPulseIds = resolvedPulseIds.filter((pulseId) => !PULSE_ID_PATTERN.test(pulseId))
    if (invalidPulseIds.length > 0) {
      pushToast(
        `Invalid pulse ID(s): ${invalidPulseIds.join(', ')}. Expected 24 alphanumeric characters.`,
        'error',
      )
      return
    }

    // When the analyst has explicitly selected pulses, dump only those.
    // Only fall back to the broad keyword search when no pulses are selected.
    const hasSelection = resolvedPulseIds.length > 0
    const useKeyword = sourceMode !== 'pulse' && !hasSelection
    dumpMutation.mutate({
      pulse_ids: resolvedPulseIds,
      search_query: useKeyword ? searchQuery || undefined : undefined,
      tags: [],
      type_filter: typeFilter,
    })
  }

  const triggerExport = (format: 'csv' | 'json' | 'xlsx', mode: 'basic' | 'extended') => {
    if (!dumped?.iocs?.length) return
    exportMutation.mutate({ iocs: dumped.iocs, format, mode })
  }

  return (
    <div className="space-y-6">
      <header>
        <p className="text-[10px] font-semibold uppercase tracking-widest text-neutral-500">Extraction Pipeline</p>
        <h1 className="mt-1 text-2xl font-semibold">IOC Dumper</h1>
      </header>

      <Panel title="Source Selection">
        <div className="flex flex-wrap gap-2">
          {SOURCE_MODES.map((mode) => (
            <Button
              key={mode.id}
              variant={sourceMode === mode.id ? 'primary' : 'ghost'}
              onClick={() => setSourceMode(mode.id)}
            >
              {mode.label}
            </Button>
          ))}
        </div>

        <div className="mt-4 grid gap-3 md:grid-cols-2">
          {sourceMode === 'pulse' ? (
            <input
              value={pulseIdsInput}
              onChange={(e) => setPulseIdsInput(e.target.value)}
              placeholder="Comma-separated pulse IDs"
              className="border border-line bg-surface-0 px-3 py-2 font-data text-sm"
              aria-label="Pulse IDs"
            />
          ) : (
            <input
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder={
                sourceMode === 'malware'
                  ? 'Malware family query'
                  : sourceMode === 'threat_actor'
                    ? 'Threat actor query'
                    : 'Keyword or tag query'
              }
              className="border border-line bg-surface-0 px-3 py-2 font-data text-sm"
              aria-label="Search query"
            />
          )}
          <Button onClick={triggerDump}>Run Dump</Button>
        </div>
      </Panel>

      {sourceMode !== 'pulse' && (
        <Panel title="Preview and Select Pulses">
          {previewQuery.isLoading && <SkeletonCard />}
          {previewQuery.data?.results.length === 0 && searchQuery && (
            <EmptyState title="Query executed - no matching pulses" />
          )}
          <div className="grid gap-2">
            {previewQuery.data?.results.map((pulse: Pulse) => (
              <div key={pulse.id} className="row-hover border border-line bg-surface-2 px-3 py-2">
                <Checkbox
                  label={pulse.name}
                  checked={selectedPulseIds.includes(pulse.id)}
                  onChange={() => togglePulse(pulse.id)}
                />
                <p className="mt-1 font-data text-[10px] text-neutral-500">{pulse.id}</p>
              </div>
            ))}
          </div>
        </Panel>
      )}

      <Panel title="Type Filter">
        <div className="flex flex-wrap gap-2">
          {FILTER_CHIPS.map((chip) => (
            <button
              key={chip.id}
              type="button"
              onClick={() => setTypeFilter(chip.id)}
              className={
                typeFilter === chip.id
                  ? 'border border-accent bg-accent/10 px-3 py-1 text-xs font-semibold uppercase tracking-wide text-accent'
                  : 'border border-line bg-surface-2 px-3 py-1 text-xs font-semibold uppercase tracking-wide text-neutral-400 transition-colors duration-150 ease-out hover:text-neutral-200'
              }
            >
              {chip.label}
            </button>
          ))}
        </div>
      </Panel>

      {dumpMutation.isPending && (
        <Panel title="Live Ingest">
          <p className="mb-2 text-xs text-neutral-500">Fetching indicators from OTX...</p>
          <ProgressBar value={progress} />
          <div className="mt-3 space-y-2">
            <SkeletonCard />
            <SkeletonCard />
          </div>
        </Panel>
      )}

      {dumped && (
        <>
          <IocPreview iocs={dumped.iocs} pulsesProcessed={dumped.pulses_processed} pulseContexts={dumped.pulse_contexts} />
          <Panel title="Export">
            <div className="flex flex-wrap gap-2">
              <Button onClick={() => triggerExport('csv', 'basic')} disabled={exportMutation.isPending}>
                Export CSV
              </Button>
              <Button onClick={() => triggerExport('json', 'extended')} disabled={exportMutation.isPending}>
                Export JSON
              </Button>
              <Button onClick={() => triggerExport('xlsx', 'extended')} disabled={exportMutation.isPending}>
                Export Excel
              </Button>
            </div>
            {exportMutation.isPending && <p className="mt-3 text-xs text-neutral-500">Generating export artifact...</p>}
          </Panel>
        </>
      )}

      <Modal open={exportResult !== null} onClose={() => setExportResult(null)} title="Export Complete">
        {exportResult && (
          <div className="space-y-4">
            <div className="flex items-center gap-3">
              <CheckCircle2 className="h-8 w-8 text-success" aria-hidden="true" />
              <div>
                <p className="text-sm font-semibold text-[#F5F5F5]">
                  {exportResult.ioc_count} IOCs exported
                </p>
                <p className="font-data text-xs text-neutral-500">{exportResult.filename}</p>
              </div>
            </div>
            <div className="flex flex-wrap gap-3 text-xs text-neutral-400">
              <span>
                Format: <span className="font-data uppercase text-neutral-200">{exportResult.format}</span>
              </span>
              <span>
                Mode: <span className="font-data uppercase text-neutral-200">{exportResult.mode}</span>
              </span>
            </div>
            <a
              className="inline-flex items-center gap-2 border border-accent bg-accent/10 px-3 py-2 text-xs font-semibold uppercase tracking-wide text-accent rounded-[2px]"
              href={`http://localhost:8000${exportResult.download_url}`}
              target="_blank"
              rel="noreferrer"
            >
              <Download className="h-3.5 w-3.5" />
              Download {exportResult.filename}
            </a>
          </div>
        )}
      </Modal>
    </div>
  )
}
