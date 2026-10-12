import type { Summary } from '../../api/types'
import StatusBadge from '../../components/StatusBadge'
import { describeRule, fmtInt } from '../../lib/format'

/** NFR-3: for the numbers on screen, which deliveries fed them and which rules reshaped them. */
export default function LineagePanel({ lineage }: { lineage: Summary['lineage'] }) {
  const rules = Object.entries(lineage.transforms).sort((a, b) => b[1] - a[1])
  return (
    <details className="lineage">
      <summary>Where do these numbers come from?</summary>
      <div className="lineage-body">
        <div>
          <h3>Deliveries included</h3>
          <ul>
            {lineage.deliveries.map((d) => (
              <li key={d.delivery_id}>
                <StatusBadge health={d.health} /> {d.filename} <span className="muted">({fmtInt(d.rows)} rows)</span>
              </li>
            ))}
          </ul>
        </div>
        <div>
          <h3>Adjustments applied</h3>
          {rules.length === 0 ? (
            <p className="muted">None. These rows were used exactly as delivered.</p>
          ) : (
            <ul>
              {rules.map(([rule, count]) => (
                <li key={rule}>
                  {describeRule(rule)} <span className="muted">({fmtInt(count)} rows)</span>
                </li>
              ))}
            </ul>
          )}
        </div>
      </div>
    </details>
  )
}
