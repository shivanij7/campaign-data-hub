import { humanize } from '../../lib/format'

type Row = Record<string, unknown>

const isRowArray = (v: unknown): v is Row[] =>
  Array.isArray(v) && v.length > 0 && v.every((x) => typeof x === 'object' && x !== null && !Array.isArray(x))

function show(v: unknown): string {
  if (v === null || v === undefined) return '\u2014'
  if (Array.isArray(v)) return v.map(show).join(', ')
  if (typeof v === 'object') return Object.entries(v).map(([k, x]) => `${k}: ${show(x)}`).join(', ')
  return String(v)
}

/**
 * Renders a check's evidence without knowing which check it is: lists of records
 * (examples, missing cells) become tables, everything else becomes labelled facts.
 */
export default function CheckDetails({ details }: { details: Row }) {
  const entries = Object.entries(details)
  const tables = entries.filter(([, v]) => isRowArray(v)) as [string, Row[]][]
  const facts = entries.filter(([, v]) => !isRowArray(v))
  return (
    <div className="check-details">
      {facts.length > 0 && (
        <dl className="facts">
          {facts.map(([k, v]) => (
            <div key={k}>
              <dt>{humanize(k)}</dt>
              <dd>{show(v)}</dd>
            </div>
          ))}
        </dl>
      )}
      {tables.map(([key, rows]) => {
        const cols = Object.keys(rows[0])
        return (
          <div key={key} className="table-wrap">
            <table className="mini">
              <caption>{humanize(key)}</caption>
              <thead>
                <tr>
                  {cols.map((c) => (
                    <th key={c}>{humanize(c)}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {rows.map((r, i) => (
                  <tr key={i}>
                    {cols.map((c) => (
                      <td key={c} className="wrap">
                        {show(r[c])}
                      </td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )
      })}
    </div>
  )
}
