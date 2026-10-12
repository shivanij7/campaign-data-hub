import type { Platform } from '../api/types'

const usd = (digits: number) =>
  new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD', minimumFractionDigits: digits, maximumFractionDigits: digits })
const usd2 = usd(2)
const usd3 = usd(3)
const int = new Intl.NumberFormat('en-US')
const pct = new Intl.NumberFormat('en-US', { style: 'percent', minimumFractionDigits: 2, maximumFractionDigits: 2 })

export const NONE = '\u2014' // shown when a ratio is undefined (zero denominator)

export const fmtSpend = (v: number) => usd2.format(v)
export const fmtInt = (v: number) => int.format(v)
export const fmtCtr = (v: number | null) => (v === null ? NONE : pct.format(v))
export const fmtCpc = (v: number | null) => (v === null ? NONE : usd3.format(v))

export const PLATFORM_LABEL: Record<Platform, string> = {
  meta_ads: 'Meta Ads',
  google_ads: 'Google Ads',
  linkedin_ads: 'LinkedIn Ads',
}

/** Plain-language names for the backend's transformation rules (NFR-3 lineage). */
export function describeRule(rule: string): string {
  if (rule === 'micros/1e6') return 'Google cost converted from micros to dollars'
  if (rule.startsWith('fx ')) return `Converted to USD (${rule.slice(3)})`
  const known: Record<string, string> = {
    unit_scale: 'Spend rescaled after a unit error was detected in the delivery',
    campaign_case: 'Campaign name capitalization unified',
    campaign_whitespace: 'Extra spaces trimmed from campaign name',
    date_format_deviation: 'Non-standard date format parsed',
  }
  return known[rule] ?? rule
}

/** "2026-06-08" -> "Jun 8" (built from parts so the browser's timezone can never shift the day). */
export function fmtWeek(iso: string): string {
  const [y, m, d] = iso.split('-').map(Number)
  return new Date(y, m - 1, d).toLocaleDateString('en-US', { month: 'short', day: 'numeric' })
}

export const humanize = (s: string) => s.replace(/_/g, ' ').replace(/^./, (c) => c.toUpperCase())
