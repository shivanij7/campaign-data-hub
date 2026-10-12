import { useState } from 'react'
import { errorMessage, getSummary } from '../../api/client'
import type { GroupBy, SortKey } from '../../api/types'
import { EmptyState, ErrorNotice } from '../../components/Notice'
import { useApi } from '../../hooks/useApi'
import FilterBar from './FilterBar'
import { NO_FILTERS, type Filters } from './filters'
import LineagePanel from './LineagePanel'
import MetricsTable, { type Sort } from './MetricsTable'
import TotalsStrip from './TotalsStrip'

interface Props {
  dataVersion: number // bumps after an ingestion so this view refetches
  ingesting: boolean
  onRunIngestion: () => void
}

export default function MetricsView({ dataVersion, ingesting, onRunIngestion }: Props) {
  const [filters, setFilters] = useState<Filters>(NO_FILTERS)
  const [groupBy, setGroupBy] = useState<GroupBy>('campaign')
  const [sort, setSort] = useState<Sort>({ key: 'spend_usd', order: 'desc' })

  const rangeError =
    filters.dateFrom && filters.dateTo && filters.dateFrom > filters.dateTo ? 'The start date is after the end date.' : null
  const params = { ...filters, groupBy, sortBy: sort.key, order: sort.order }
  const { data, error, loading, reload } = useApi(
    (signal) => getSummary(params, signal),
    JSON.stringify([params, dataVersion]),
    !rangeError,
  )

  // Clicking the active column flips direction; a new column starts descending (ascending for text).
  const onSort = (key: SortKey) =>
    setSort((s) =>
      s.key === key
        ? { key, order: s.order === 'asc' ? 'desc' : 'asc' }
        : { key, order: key === 'campaign' || key === 'platform' ? 'asc' : 'desc' },
    )
  const changeGroupBy = (g: GroupBy) => {
    setGroupBy(g)
    if (g === 'platform' && sort.key === 'campaign') setSort({ key: 'spend_usd', order: 'desc' })
  }

  const filtersActive = Boolean(filters.platform || filters.dateFrom || filters.dateTo)

  let body
  if (error) {
    body = <ErrorNotice message={errorMessage(error)} onRetry={reload} />
  } else if (!data) {
    body = rangeError ? null : <p className="muted">Loading metrics…</p>
  } else if (data.groups.length === 0) {
    body = filtersActive ? (
      <EmptyState title="No campaigns match these filters">
        <button className="btn" onClick={() => setFilters(NO_FILTERS)}>
          Clear filters
        </button>
      </EmptyState>
    ) : (
      <EmptyState title="No metrics loaded yet">
        <p>Run ingestion to load the delivery files from the data folder.</p>
        <button className="btn btn-primary" onClick={onRunIngestion} disabled={ingesting}>
          {ingesting ? 'Running ingestion…' : 'Run ingestion'}
        </button>
      </EmptyState>
    )
  } else {
    body = (
      <div className={loading ? 'is-updating' : undefined} aria-busy={loading}>
        <TotalsStrip summary={data} />
        <MetricsTable groups={data.groups} groupBy={groupBy} sort={sort} onSort={onSort} />
        <LineagePanel lineage={data.lineage} />
      </div>
    )
  }

  return (
    <>
      <h1>Campaign metrics</h1>
      <FilterBar filters={filters} groupBy={groupBy} rangeError={rangeError} onFilters={setFilters} onGroupBy={changeGroupBy} />
      {body}
    </>
  )
}
