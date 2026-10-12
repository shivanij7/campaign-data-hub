import type { Delivery, Platform } from '../../api/types'
import { PLATFORM_LABEL, fmtWeek } from '../../lib/format'

const PLATFORMS = Object.keys(PLATFORM_LABEL) as Platform[]
const STATUS_WORD = { pass: 'Pass', warn: 'Warning', fail: 'Fail' }

function cellLabel(d: Delivery): string {
  if (!d.received) return 'Missing'
  if (d.filename.includes('_resend')) return 'Resend'
  return STATUS_WORD[d.health]
}

interface Props {
  deliveries: Delivery[]
  selected: string | null
  onSelect: (filename: string) => void
}

/**
 * Platform x week. One glance shows which deliveries are healthy, which arrived damaged and which
 * never arrived. A cell can hold two deliveries (an original plus its resend).
 */
export default function DeliveryGrid({ deliveries, selected, onSelect }: Props) {
  const weeks = [...new Set(deliveries.map((d) => d.week_start).filter((w) => w !== 'unknown'))].sort()
  return (
    <div className="table-wrap">
      <table className="grid">
        <caption className="sr-only">Deliveries by platform and week; select one to see its quality report</caption>
        <thead>
          <tr>
            <th scope="col">Platform</th>
            {weeks.map((w) => (
              <th key={w} scope="col">
                Week of {fmtWeek(w)}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {PLATFORMS.map((p) => (
            <tr key={p}>
              <th scope="row">{PLATFORM_LABEL[p]}</th>
              {weeks.map((w) => (
                <td key={w}>
                  {deliveries
                    .filter((d) => d.platform === p && d.week_start === w)
                    .map((d) => {
                      const issues = d.check_counts.fail + d.check_counts.warn
                      return (
                        <button
                          key={d.filename}
                          className={`cell cell-${d.health}`}
                          aria-pressed={selected === d.filename}
                          aria-label={`${d.filename}: ${cellLabel(d)}`}
                          onClick={() => onSelect(d.filename)}
                        >
                          <span>{cellLabel(d)}</span>
                          {issues > 0 && <small>{issues === 1 ? '1 issue' : `${issues} issues`}</small>}
                        </button>
                      )
                    })}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
