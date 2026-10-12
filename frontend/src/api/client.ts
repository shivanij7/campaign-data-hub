import type { Delivery, DeliveryDetail, GroupBy, IngestResult, Order, Platform, SortKey, Summary } from './types'

const BASE = import.meta.env.VITE_API_BASE ?? '/api/v1'

/** Every failure the UI can see: HTTP errors from the API's standard error body, or network failure (status 0). */
export class ApiError extends Error {
  status: number
  code: string
  constructor(status: number, code: string, message: string) {
    super(message)
    this.status = status
    this.code = code
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  let res: Response
  try {
    res = await fetch(BASE + path, init)
  } catch (err) {
    if (err instanceof DOMException && err.name === 'AbortError') throw err
    throw new ApiError(0, 'network_error', 'Cannot reach the API. Check that the backend is running on port 8000.')
  }
  if (!res.ok) {
    const body = await res.json().catch(() => null)
    const e = body?.error
    throw new ApiError(res.status, e?.code ?? 'http_error', e?.message ?? `Request failed (HTTP ${res.status}).`)
  }
  return res.json() as Promise<T>
}

export interface SummaryParams {
  platform: Platform | ''
  dateFrom: string
  dateTo: string
  groupBy: GroupBy
  sortBy: SortKey
  order: Order
}

export function getSummary(p: SummaryParams, signal: AbortSignal): Promise<Summary> {
  const q = new URLSearchParams({ group_by: p.groupBy, sort_by: p.sortBy, order: p.order })
  if (p.platform) q.set('platform', p.platform)
  if (p.dateFrom) q.set('date_from', p.dateFrom)
  if (p.dateTo) q.set('date_to', p.dateTo)
  return request<Summary>(`/metrics/summary?${q}`, { signal })
}

export function getDeliveries(signal: AbortSignal): Promise<Delivery[]> {
  return request<Delivery[]>('/deliveries', { signal })
}

export function getDelivery(id: number, signal: AbortSignal): Promise<DeliveryDetail> {
  return request<DeliveryDetail>(`/deliveries/${id}`, { signal })
}

export function runIngestion(): Promise<IngestResult> {
  return request<IngestResult>('/ingestions', { method: 'POST' })
}

export function errorMessage(err: unknown): string {
  return err instanceof Error ? err.message : 'Something went wrong.'
}
