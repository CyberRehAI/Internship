import { Download, Trash2 } from 'lucide-react'
import { downloadUrl } from '../api/client'
import { Badge } from '../components/ui/Badge'
import { Button } from '../components/ui/Button'
import { EmptyState } from '../components/ui/EmptyState'
import { Panel } from '../components/ui/Panel'
import { useLocalStorage } from '../hooks/useLocalStorage'

export function ExportHistoryPage() {
  const [history, setHistory] = useLocalStorage<
    Array<{ exportId: string; filename: string; format: string; mode: string; iocCount: number; timestamp: string }>
  >('otx_export_history', [])

  const removeEntry = (exportId: string) => {
    setHistory((prev) => prev.filter((item) => item.exportId !== exportId))
  }

  return (
    <div className="space-y-6">
      <header>
        <p className="text-[10px] font-semibold uppercase tracking-widest text-neutral-500">Artifact Registry</p>
        <h1 className="mt-1 text-2xl font-semibold">Export History</h1>
      </header>

      {history.length === 0 ? (
        <EmptyState title="No exports generated" description="Run an IOC dump export to populate history." />
      ) : (
        <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-3">
          {history.map((item) => (
            <Panel key={item.exportId} className="!p-0">
              <div className="space-y-3 p-4">
                <p className="font-data text-sm text-[#F5F5F5]">{item.filename}</p>
                <p className="font-data text-[10px] text-neutral-500">{item.timestamp}</p>
                <div className="flex flex-wrap gap-2">
                  <Badge>{item.format}</Badge>
                  <Badge>{item.mode}</Badge>
                  <Badge>{`${item.iocCount} IOCs`}</Badge>
                </div>
                <div className="flex gap-2">
                  <a
                    href={downloadUrl(item.exportId)}
                    target="_blank"
                    rel="noreferrer"
                    aria-label={`Download ${item.filename}`}
                    className="inline-flex items-center gap-2 border border-line bg-surface-2 px-3 py-2 text-xs font-semibold uppercase tracking-wide text-neutral-200 transition-colors duration-150 ease-out hover:bg-surface-1"
                  >
                    <Download className="h-3.5 w-3.5" />
                    Download
                  </a>
                  <Button
                    variant="danger"
                    aria-label={`Delete ${item.filename} from history`}
                    onClick={() => removeEntry(item.exportId)}
                  >
                    <Trash2 className="h-3.5 w-3.5" />
                    Delete
                  </Button>
                </div>
              </div>
            </Panel>
          ))}
        </div>
      )}
    </div>
  )
}
