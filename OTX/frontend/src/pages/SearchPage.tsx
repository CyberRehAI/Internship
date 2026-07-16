import { useMutation } from '@tanstack/react-query'
import { useState } from 'react'
import type { FormEvent } from 'react'
import { Link } from 'react-router-dom'
import { Globe, Hash, Link2, ShieldAlert } from 'lucide-react'
import { searchGlobal } from '../api/client'
import { Badge } from '../components/ui/Badge'
import { Button } from '../components/ui/Button'
import { EmptyState } from '../components/ui/EmptyState'
import { Panel } from '../components/ui/Panel'
import { SkeletonCard } from '../components/ui/Skeleton'
import { useLocalStorage } from '../hooks/useLocalStorage'
import type { Pulse } from '../types/otx'

function typeIcon(type: string) {
  if (type.includes('hash') || type === 'md5' || type === 'sha1' || type === 'sha256') return Hash
  if (type === 'url') return Link2
  if (type === 'cve') return ShieldAlert
  return Globe
}

function extractReputation(indicatorResult: Record<string, unknown> | null): string | null {
  if (!indicatorResult) return null
  const reputation = indicatorResult.reputation as Record<string, unknown> | undefined
  if (reputation && typeof reputation.threat_score === 'number') {
    return String(reputation.threat_score)
  }
  const general = indicatorResult.general as Record<string, unknown> | undefined
  if (general && typeof general.reputation === 'number') {
    return String(general.reputation)
  }
  return null
}

export function SearchPage() {
  const [query, setQuery] = useState('')
  const [, setRecentSearches] = useLocalStorage<
    Array<{ query: string; detectedType: string; timestamp: string }>
  >('otx_recent_searches', [])

  const searchMutation = useMutation({
    mutationFn: (searchQuery: string) => searchGlobal(searchQuery),
    onSuccess: (response) => {
      setRecentSearches((prev) =>
        [{ query: response.query, detectedType: response.detected_type, timestamp: new Date().toISOString() }, ...prev]
          .slice(0, 50)
          .filter((item, idx, arr) => arr.findIndex((inner) => inner.query === item.query) === idx),
      )
    },
  })

  const onSubmit = (event: FormEvent) => {
    event.preventDefault()
    if (query.trim().length === 0) return
    searchMutation.mutate(query.trim())
  }

  const reputation = extractReputation(searchMutation.data?.indicator_result ?? null)

  return (
    <div className="space-y-6">
      <header>
        <p className="text-[10px] font-semibold uppercase tracking-widest text-neutral-500">Indicator Lookup</p>
        <h1 className="mt-1 text-2xl font-semibold">Global Search</h1>
      </header>

      <Panel>
        <form role="search" onSubmit={onSubmit} className="flex flex-col gap-3 md:flex-row">
          <label htmlFor="global-search" className="sr-only">
            Search indicators
          </label>
          <input
            id="global-search"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="IP, domain, hash, CVE, malware family, threat actor..."
            className="w-full border border-line bg-surface-0 px-4 py-3 font-data text-sm text-neutral-200 placeholder:text-neutral-600 focus:border-accent"
          />
          <Button type="submit" className="md:min-w-32">
            Execute Query
          </Button>
        </form>
      </Panel>

      {searchMutation.isPending && (
        <div className="space-y-3">
          <p className="text-xs uppercase tracking-widest text-neutral-500">Query executing...</p>
          <SkeletonCard />
          <SkeletonCard />
        </div>
      )}

      {searchMutation.isError && (
        <EmptyState title="Query failed" description="Verify API connection and retry." />
      )}

      {searchMutation.data && (
        <section className="space-y-4">
          <div className="flex flex-wrap items-center gap-3">
            <Badge>{searchMutation.data.detected_type}</Badge>
            <span className="text-xs text-neutral-500">
              Related pulses: <span className="font-data text-neutral-300">{searchMutation.data.total_pulses}</span>
            </span>
            {reputation && (
              <span className="text-xs text-neutral-500">
                Reputation score: <span className="font-data text-accent">{reputation}</span>
              </span>
            )}
          </div>

          {searchMutation.data.pulses.length === 0 ? (
            <EmptyState title="Query executed - no matches" />
          ) : (
            <div className="grid gap-3">
              {searchMutation.data.pulses.map((pulse: Pulse) => {
                const Icon = typeIcon(searchMutation.data!.detected_type)
                return (
                  <article key={pulse.id} className="panel-surface row-hover p-4">
                    <div className="flex flex-wrap items-start justify-between gap-3">
                      <div className="flex items-start gap-3">
                        <Icon className="mt-0.5 h-4 w-4 text-accent" aria-hidden="true" />
                        <div>
                          <h2 className="text-sm font-semibold text-[#F5F5F5]">{pulse.name}</h2>
                          <p className="mt-1 text-xs text-neutral-500">{pulse.description || 'No description provided.'}</p>
                          <div className="mt-2 flex flex-wrap gap-2">
                            <Badge>{searchMutation.data!.detected_type}</Badge>
                            {pulse.tags?.slice(0, 4).map((tag) => (
                              <Badge key={tag}>{tag}</Badge>
                            ))}
                          </div>
                        </div>
                      </div>
                      <div className="flex flex-col items-end gap-2 text-right">
                        <p className="text-[10px] uppercase tracking-widest text-neutral-500">
                          Related pulses: <span className="font-data text-neutral-300">{searchMutation.data!.total_pulses}</span>
                        </p>
                        <Link
                          to={`/pulses?id=${pulse.id}`}
                          className="inline-flex items-center justify-center border border-line bg-surface-2 px-3 py-2 text-xs font-semibold uppercase tracking-wide text-neutral-200 transition-colors duration-150 ease-out hover:bg-surface-1"
                        >
                          View
                        </Link>
                      </div>
                    </div>
                  </article>
                )
              })}
            </div>
          )}
        </section>
      )}
    </div>
  )
}
