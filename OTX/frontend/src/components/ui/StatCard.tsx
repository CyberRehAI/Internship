import { Panel } from './Panel'

type StatCardProps = {
  label: string
  value: string | number
  caption?: string
}

export function StatCard({ label, value, caption }: StatCardProps) {
  return (
    <Panel className="!p-0 glow-card">
      <div className="p-4">
        <p className="text-[10px] font-semibold uppercase tracking-widest text-neutral-500">{label}</p>
        <p className="mt-2 font-data text-2xl font-semibold text-accent">{value}</p>
        {caption && <p className="mt-1 text-xs text-neutral-500">{caption}</p>}
      </div>
    </Panel>
  )
}
