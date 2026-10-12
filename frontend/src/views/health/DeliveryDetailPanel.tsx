import { errorMessage, getDelivery } from '../../api/client'
import type { Check, Delivery, Health } from '../../api/types'
import { ErrorNotice } from '../../components/Notice'
import StatusBadge from '../../components/StatusBadge'
import { useApi } from '../../hooks/useApi'
import { PLATFORM_LABEL, fmtInt, fmtWeek, humanize } from '../../lib/format'
import CheckDetails from './CheckDetails'

const ORDER: Record<Health, number> = { fail: 0, warn: 1, pass: 2 }

function CheckItem({ check }: { check: Check }) {
  const hasDetails = Object.keys(check.details).length > 0
  return (
    <li className="check">
      <div className="check-head">
        <StatusBadge health={check.status} />
        <strong>{humanize(check.name)}</strong>
        <span className="muted">{check.level}-level</span>
      </div>
      <p>{check.summary}</p>
      {/* Problems open by default; passing checks keep their evidence one click away. */}
      {hasDetails && (
        <details open={check.status !== 'pass'}>
          <summary>Evidence</summary>
          <CheckDetails details={check.details} />
        </details>
      )}
    </li>
  )
}

interface Props {
  delivery: Delivery
  dataVersion: number
}

export default function DeliveryDetailPanel({ delivery, dataVersion }: Props) {
  const { data, error, reload } = useApi((signal) => getDelivery(delivery.id, signal), `delivery#${delivery.id}#${dataVersion}`)
  const checks = data ? [...data.checks].sort((a, b) => ORDER[a.status] - ORDER[b.status]) : []
  const week = delivery.week_start === 'unknown' ? 'unknown week' : `week of ${fmtWeek(delivery.week_start)}`

  return (
    <section className="detail" aria-label={`Quality report for ${delivery.filename}`}>
      <header className="detail-head">
        <h2>{delivery.filename}</h2>
        <StatusBadge health={delivery.health} />
      </header>
      <p className="muted">
        {delivery.platform === 'unknown' ? 'Unknown platform' : PLATFORM_LABEL[delivery.platform]}, {week}.{' '}
        {delivery.received
          ? `${fmtInt(delivery.rows_read)} rows read, ${fmtInt(delivery.rows_loaded)} loaded, ${fmtInt(delivery.rows_quarantined)} excluded.`
          : 'This delivery never arrived.'}
      </p>

      {error ? (
        <ErrorNotice message={errorMessage(error)} onRetry={reload} />
      ) : !data ? (
        <p className="muted">Loading report…</p>
      ) : (
        <>
          <h3>Checks</h3>
          <ul className="checks">
            {checks.map((c) => (
              <CheckItem key={c.name} check={c} />
            ))}
          </ul>

          {data.quarantined_rows.length > 0 && (
            <>
              <h3>Excluded rows ({data.quarantined_rows.length})</h3>
              <p className="muted">These rows were not loaded into the metrics. The original values are kept here.</p>
              <div className="table-wrap">
                <table className="mini">
                  <thead>
                    <tr>
                      <th className="num">Row</th>
                      <th>Reason</th>
                      <th>Field</th>
                      <th>Detail</th>
                      <th>Original values</th>
                    </tr>
                  </thead>
                  <tbody>
                    {data.quarantined_rows.map((q, i) => (
                      <tr key={i}>
                        <td className="num">{q.source_row}</td>
                        <td>{humanize(q.code)}</td>
                        <td>{q.field ?? '\u2014'}</td>
                        <td className="wrap">{q.message}</td>
                        <td className="wrap">
                          <code>{q.raw ? JSON.stringify(q.raw) : '\u2014'}</code>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </>
          )}
        </>
      )}
    </section>
  )
}
