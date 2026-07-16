export type IocCategory = 'ip' | 'domains' | 'urls' | 'file_hashes' | 'cves' | 'email_addresses' | 'yara' | 'other'

type IocTypeMeta = {
  label: string
  category: IocCategory
  badgeClass: string
}

// Category color language, aligned with the design tokens.
const CATEGORY_BADGE: Record<IocCategory, string> = {
  ip: 'border-accent/40 bg-accent/10 text-accent',
  domains: 'border-violet-500/40 bg-violet-500/10 text-violet-300',
  urls: 'border-amber-500/40 bg-amber-500/10 text-amber-300',
  file_hashes: 'border-emerald-500/40 bg-emerald-500/10 text-emerald-300',
  cves: 'border-rose-500/40 bg-rose-500/10 text-rose-300',
  email_addresses: 'border-pink-500/40 bg-pink-500/10 text-pink-300',
  yara: 'border-indigo-500/40 bg-indigo-500/10 text-indigo-300',
  other: 'border-neutral-500/40 bg-neutral-500/10 text-neutral-300',
}

// Map raw OTX indicator types to a short label + category.
const TYPE_META: Record<string, { label: string; category: IocCategory }> = {
  IPv4: { label: 'IPv4', category: 'ip' },
  IPv6: { label: 'IPv6', category: 'ip' },
  CIDR: { label: 'CIDR', category: 'ip' },
  domain: { label: 'Domain', category: 'domains' },
  hostname: { label: 'Hostname', category: 'domains' },
  URL: { label: 'URL', category: 'urls' },
  URI: { label: 'URI', category: 'urls' },
  'FileHash-MD5': { label: 'MD5', category: 'file_hashes' },
  'FileHash-SHA1': { label: 'SHA1', category: 'file_hashes' },
  'FileHash-SHA256': { label: 'SHA256', category: 'file_hashes' },
  'FileHash-PEHASH': { label: 'PEHASH', category: 'file_hashes' },
  'FileHash-IMPHASH': { label: 'IMPHASH', category: 'file_hashes' },
  email: { label: 'Email', category: 'email_addresses' },
  CVE: { label: 'CVE', category: 'cves' },
  YARA: { label: 'YARA', category: 'yara' },
  FilePath: { label: 'FilePath', category: 'other' },
  Mutex: { label: 'Mutex', category: 'other' },
}

export function getIocTypeMeta(type: string): IocTypeMeta {
  const meta = TYPE_META[type] ?? { label: type || 'Unknown', category: 'other' as IocCategory }
  return { ...meta, badgeClass: CATEGORY_BADGE[meta.category] }
}

export const FILTER_LABELS: Array<{ id: IocCategory | 'all'; label: string }> = [
  { id: 'all', label: 'All' },
  { id: 'ip', label: 'IP' },
  { id: 'domains', label: 'Domain' },
  { id: 'urls', label: 'URL' },
  { id: 'file_hashes', label: 'Hash' },
  { id: 'email_addresses', label: 'Email' },
  { id: 'cves', label: 'CVE' },
  { id: 'yara', label: 'YARA' },
]

// Build an OTX indicator deep-link where possible, else a global search.
export function otxIndicatorUrl(type: string, value: string): string {
  const { category } = getIocTypeMeta(type)
  const encoded = encodeURIComponent(value)
  switch (category) {
    case 'ip':
      return `https://otx.alienvault.com/indicator/ip/${encoded}`
    case 'domains':
      return type === 'hostname'
        ? `https://otx.alienvault.com/indicator/hostname/${encoded}`
        : `https://otx.alienvault.com/indicator/domain/${encoded}`
    case 'urls':
      return `https://otx.alienvault.com/indicator/url/${encoded}`
    case 'file_hashes':
      return `https://otx.alienvault.com/indicator/file/${encoded}`
    case 'cves':
      return `https://otx.alienvault.com/indicator/cve/${encoded}`
    default:
      return `https://otx.alienvault.com/browse/global?q=${encoded}`
  }
}
