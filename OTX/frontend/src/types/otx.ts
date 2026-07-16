export type SearchResponse = {
  query: string
  detected_type: string
  search_strategy: string
  indicator_result: Record<string, unknown> | null
  pulses: Pulse[]
  total_pulses: number
}

export type Pulse = {
  id: string
  name: string
  description?: string
  author_name?: string
  created?: string
  modified?: string
  visibility?: string
  tags: string[]
  TLP?: string
  adversary?: string
  targeted_countries: string[]
  attack_ids: string[]
  malware_families: string[]
  references: string[]
  indicator_count?: number
}

export type IOCRecord = {
  type: string
  value: string
  description?: string
  pulse_id?: string
  pulse_name?: string
  author?: string
  created?: string
  tags: string[]
  references: string[]
  malware_families: string[]
  attack_ids: string[]
  tlp?: string
  related_pulses: Array<{ pulse_id: string; pulse_name?: string }>
  related_pulse_count: number
}

export type PulseIntelligenceContext = {
  pulse_id: string
  immediate_threat: string
  threat_summary?: string
  pulse_name?: string
  author?: string
  created?: string
  tlp?: string
  tags: string[]
  adversary?: string
  targeted_countries: string[]
  malware_families: string[]
  attack_ids: string[]
  references: string[]
}

export type IOCDumpResponse = {
  iocs: IOCRecord[]
  stats: {
    by_type: Record<string, number>
    total: number
    unique: number
  }
  pulses_processed: number
  pulse_contexts: PulseIntelligenceContext[]
}

export type ExportResponse = {
  export_id: string
  filename: string
  format: 'csv' | 'json' | 'xlsx'
  mode: 'basic' | 'extended'
  ioc_count: number
  created_at: string
  download_url: string
}
