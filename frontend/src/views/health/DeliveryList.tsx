import type { Delivery, Health } from '../../api/types'
import StatusBadge from '../../components/StatusBadge'
import { fmtInt } from '../../lib/format'

const SEVERITY: Record<Health, number> = { fail: 0, warn: 1, pass: 2 }

/** Worst problems first, then chronological, so the rows that need attention are at the top. */
function bySeverity(a: Delivery, b: Delivery): number {
  return SEVERITY[a.health] - SEVERITY[b.health] || a.week_start.localeCompare(b.week_start) || a.filename.localeCompare(b.filename)
}

function mainFinding(d: Delivery): string {
  if (d.problems.length === 0) return 'All checks passed'
  const worst = d.problems.find((p) => p.status === 'fail') ?? d.problems[0]
  const more = d.problems.length - 1
  return more > 0 ? `${worst.summary} (+${more} more)` : worst.summary
}

interface Props {
  deliveries: Delivery[]
  selected: string | null
  onSelect: (filename: string) => void
}

export default function DeliveryList({ deliveries, selected, onSelect }: Props) {
  return (
    <div className="table-wrap">
      <table className="list">
        <thead>
          <tr>
            <th>Delivery</th>
            <th>Status</th>
            <th className="num">Rows loaded</th>
            <th>Main finding</th>
          </tr>
        </thead>
        <tbody>
          {[...deliveries].sort(bySeverity).map((d) => (
            <tr key={d.filename} className={selected === d.filename ? 'is-selected' : undefined}>
              <th scope="row">
                <button className="link" onClick={() => onSelect(d.filename)} aria-pressed={selected === d.filename}>
                  {d.filename}
                </button>
              </th>
              <td>
                <StatusBadge health={d.health} />
              </td>
              <td className="num">{d.received ? `${fmtInt(d.rows_loaded)} of ${fmtInt(d.rows_read)}` : 'None'}</td>
              <td className="wrap">{mainFinding(d)}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
