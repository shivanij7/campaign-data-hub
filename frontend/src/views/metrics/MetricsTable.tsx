import type { GroupBy, GroupRow, Order, SortKey } from '../../api/types'
import { NONE, PLATFORM_LABEL, fmtCpc, fmtCtr, fmtInt, fmtSpend } from '../../lib/format'

export interface Sort {
  key: SortKey
  order: Order
}

interface Column {
  key: SortKey
  label: string
  numeric: boolean
}

const COLUMNS: Column[] = [
  { key: 'campaign', label: 'Campaign', numeric: false },
  { key: 'platform', label: 'Platform', numeric: false },
  { key: 'spend_usd', label: 'Spend (USD)', numeric: true },
  { key: 'impressions', label: 'Impressions', numeric: true },
  { key: 'clicks', label: 'Clicks', numeric: true },
  { key: 'ctr', label: 'CTR', numeric: true },
  { key: 'cpc', label: 'CPC', numeric: true },
]

interface Props {
  groups: GroupRow[]
  groupBy: GroupBy
  sort: Sort
  onSort: (key: SortKey) => void
}

export default function MetricsTable({ groups, groupBy, sort, onSort }: Props) {
  const columns = groupBy === 'platform' ? COLUMNS.filter((c) => c.key !== 'campaign') : COLUMNS
  return (
    <div className="table-wrap">
      <table>
        <thead>
          <tr>
            {columns.map((c) => {
              const active = sort.key === c.key
              return (
                <th
                  key={c.key}
                  className={c.numeric ? 'num' : undefined}
                  aria-sort={active ? (sort.order === 'asc' ? 'ascending' : 'descending') : 'none'}
                >
                  <button className="sort" onClick={() => onSort(c.key)}>
                    {c.label}
                    <span aria-hidden="true" className="sort-mark">
                      {active ? (sort.order === 'asc' ? '\u25B2' : '\u25BC') : ''}
                    </span>
                  </button>
                </th>
              )
            })}
          </tr>
        </thead>
        <tbody>
          {groups.map((g) => (
            <tr key={`${g.platform}/${g.campaign ?? ''}`}>
              {groupBy === 'campaign' && <th scope="row">{g.campaign}</th>}
              {groupBy === 'platform' ? <th scope="row">{PLATFORM_LABEL[g.platform]}</th> : <td>{PLATFORM_LABEL[g.platform]}</td>}
              <td className="num">{fmtSpend(g.spend_usd)}</td>
              <td className="num">{fmtInt(g.impressions)}</td>
              <td className="num">{fmtInt(g.clicks)}</td>
              <td className="num">{fmtCtr(g.ctr)}</td>
              <td className="num" title={g.cpc === null ? 'No clicks, so cost per click is undefined' : undefined}>
                {g.cpc === null ? NONE : fmtCpc(g.cpc)}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
