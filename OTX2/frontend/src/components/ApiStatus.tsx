import { useQuery } from '@tanstack/react-query'
import { getHealth } from '../api/client'

export function ApiStatus() {
  const { data, isLoading, isError } = useQuery({ queryKey: ['health'], queryFn: getHealth })

  if (isLoading) {
    return <span className="rounded bg-neutral-800 px-2 py-1 text-xs text-neutral-300">Checking API...</span>
  }
  if (isError) {
    return <span className="rounded bg-red-950 px-2 py-1 text-xs text-red-300">API Error</span>
  }
  return (
    <span className="rounded bg-emerald-950 px-2 py-1 text-xs text-emerald-300">
      Connected as {data?.otx_user ?? 'unknown'}
    </span>
  )
}
