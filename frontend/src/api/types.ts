// Mirrors the FastAPI response models (backend/app/schemas.py).
export type Platform = 'meta_ads' | 'google_ads' | 'linkedin_ads'
export type Health = 'pass' | 'warn' | 'fail'
export type GroupBy = 'campaign' | 'platform'
export type SortKey = 'campaign' | 'platform' | 'spend_usd' | 'impressions' | 'clicks' | 'ctr' | 'cpc'
export type Order = 'asc' | 'desc'

export interface Derived {
  spend_usd: number
  impressions: number
  clicks: number
  ctr: number | null // null when impressions = 0
  cpc: number | null // null when clicks = 0
}

export interface GroupRow extends Derived {
  platform: Platform
  campaign: string | null // null when grouped by platform
  rows: number
}

export interface SourceDelivery {
  delivery_id: number
  filename: string
  health: Health
  rows: number
}

export interface Summary {
  group_by: GroupBy
  totals: Derived
  groups: GroupRow[]
  lineage: { deliveries: SourceDelivery[]; transforms: Record<string, number> }
}

export interface IngestResult {
  mode: 'full' | 'single'
  errors: { filename: string; error: string }[]
  health_counts: Partial<Record<Health, number>>
}

// ---------- data health ----------
export interface Problem {
  check: string
  status: Health
  summary: string
}

export interface Delivery {
  id: number
  platform: Platform | 'unknown'
  week_start: string // ISO date, or 'unknown' for files whose name we could not read
  filename: string
  received: boolean // false = expected but never arrived
  health: Health
  rows_read: number
  rows_loaded: number
  rows_quarantined: number
  ingested_at: string
  check_counts: Record<Health, number>
  problems: Problem[] // the non-passing checks
}

export interface Check {
  name: string
  level: 'row' | 'file' | 'delivery'
  status: Health
  summary: string
  details: Record<string, unknown>
}

export interface QuarantinedRow {
  source_row: number
  code: string
  field: string | null
  message: string
  raw: Record<string, unknown> | null
}

export interface DeliveryDetail extends Delivery {
  content_hash: string | null
  checks: Check[]
  quarantined_rows: QuarantinedRow[]
}
