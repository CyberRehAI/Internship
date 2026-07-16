type EmptyStateProps = {
  title: string
  description?: string
}

export function EmptyState({ title, description }: EmptyStateProps) {
  return (
    <div className="panel-surface border-dashed p-6 text-center">
      <p className="text-sm font-semibold uppercase tracking-widest text-neutral-400">{title}</p>
      {description && <p className="mt-2 text-xs text-neutral-500">{description}</p>}
    </div>
  )
}
