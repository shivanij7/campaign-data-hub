import type { GroupBy, Platform } from '../../api/types'
import { PLATFORM_LABEL } from '../../lib/format'
import { NO_FILTERS, type Filters } from './filters'

interface Props {
  filters: Filters
  groupBy: GroupBy
  rangeError: string | null
  onFilters: (f: Filters) => void
  onGroupBy: (g: GroupBy) => void
}

export default function FilterBar({ filters, groupBy, rangeError, onFilters, onGroupBy }: Props) {
  const active = filters.platform || filters.dateFrom || filters.dateTo
  return (
    <form className="filters" onSubmit={(e) => e.preventDefault()} aria-label="Filters">
      <label>
        Platform
        <select value={filters.platform} onChange={(e) => onFilters({ ...filters, platform: e.target.value as Platform | '' })}>
          <option value="">All platforms</option>
          {(Object.keys(PLATFORM_LABEL) as Platform[]).map((p) => (
            <option key={p} value={p}>
              {PLATFORM_LABEL[p]}
            </option>
          ))}
        </select>
      </label>
      <label>
        From
        <input type="date" value={filters.dateFrom} onChange={(e) => onFilters({ ...filters, dateFrom: e.target.value })} />
      </label>
      <label>
        To
        <input type="date" value={filters.dateTo} onChange={(e) => onFilters({ ...filters, dateTo: e.target.value })} />
      </label>
      <label>
        Group by
        <select value={groupBy} onChange={(e) => onGroupBy(e.target.value as GroupBy)}>
          <option value="campaign">Campaign</option>
          <option value="platform">Platform</option>
        </select>
      </label>
      {active && (
        <button type="button" className="btn btn-quiet" onClick={() => onFilters(NO_FILTERS)}>
          Clear filters
        </button>
      )}
      {rangeError && (
        <p className="field-error" role="alert">
          {rangeError}
        </p>
      )}
    </form>
  )
}
