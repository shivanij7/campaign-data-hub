import type { Summary } from '../../api/types'
import { fmtCpc, fmtCtr, fmtInt, fmtSpend } from '../../lib/format'

/** Totals for whatever the filters currently select (computed by the API, not by summing the table). */
export default function TotalsStrip({ summary }: { summary: Summary }) {
  const t = summary.totals
  const stats: [string, string][] = [
    ['Spend', fmtSpend(t.spend_usd)],
    ['Impressions', fmtInt(t.impressions)],
    ['Clicks', fmtInt(t.clicks)],
    ['CTR', fmtCtr(t.ctr)],
    ['CPC', fmtCpc(t.cpc)],
  ]
  const days = summary.lineage.deliveries.reduce((n, d) => n + d.rows, 0)
  return (
    <section aria-label="Totals for the current filters">
      <dl className="totals">
        {stats.map(([label, value]) => (
          <div key={label}>
            <dt>{label}</dt>
            <dd>{value}</dd>
          </div>
        ))}
      </dl>
      <p className="muted">
        Built from {fmtInt(days)} campaign-days across {summary.lineage.deliveries.length} deliveries.
      </p>
    </section>
  )
}
