import axios from 'axios'
import type { ExportResponse, IOCDumpResponse, IOCRecord, Pulse, SearchResponse } from '../types/otx'

const api = axios.create({
  baseURL: 'http://localhost:8000',
  timeout: 30000,
})

export async function getHealth() {
  const { data } = await api.get('/api/health')
  return data
}

export async function searchGlobal(query: string, limit = 25): Promise<SearchResponse> {
  const { data } = await api.get('/api/search', { params: { q: query, limit } })
  return data
}

export async function searchPulses(query: string, limit = 25): Promise<{ results: Pulse[]; count: number }> {
  const { data } = await api.get('/api/pulses/search', { params: { q: query, limit } })
  return data
}

export async function getPulseDetails(pulseId: string): Promise<Pulse> {
  const { data } = await api.get(`/api/pulses/${pulseId}`)
  return data
}

// Dumping and exporting can fan out to many OTX requests, so allow a longer
// window than the default client timeout to avoid spurious client-side aborts.
const LONG_RUNNING_TIMEOUT_MS = 180000

export async function dumpIOCs(payload: {
  pulse_ids: string[]
  search_query?: string
  tags: string[]
  type_filter: string
}): Promise<IOCDumpResponse> {
  const { data } = await api.post('/api/iocs/dump', payload, { timeout: LONG_RUNNING_TIMEOUT_MS })
  return data
}

export async function exportIOCs(payload: {
  iocs: IOCRecord[]
  mode: 'basic' | 'extended'
  format: 'csv' | 'json' | 'xlsx'
}): Promise<ExportResponse> {
  const { data } = await api.post('/api/iocs/export', payload, { timeout: LONG_RUNNING_TIMEOUT_MS })
  return data
}

export async function getPulseIndicators(pulseId: string, limit = 1000): Promise<{ results: Array<Record<string, unknown>>; count: number }> {
  const { data } = await api.get(`/api/pulses/${pulseId}/indicators`, { params: { limit } })
  return data
}

export function downloadUrl(exportId: string): string {
  return `${api.defaults.baseURL}/api/exports/${exportId}/download`
}
