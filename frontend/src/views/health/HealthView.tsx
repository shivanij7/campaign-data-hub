import { useEffect, useRef, useState } from 'react'
import { errorMessage, getDeliveries } from '../../api/client'
import type { Health } from '../../api/types'
import { EmptyState, ErrorNotice } from '../../components/Notice'
import { useApi } from '../../hooks/useApi'
import DeliveryDetailPanel from './DeliveryDetailPanel'
import DeliveryGrid from './DeliveryGrid'
import DeliveryList from './DeliveryList'

interface Props {
  dataVersion: number
  ingesting: boolean
  onRunIngestion: () => void
}

export default function HealthView({ dataVersion, ingesting, onRunIngestion }: Props) {
  const { data, error, loading, reload } = useApi((signal) => getDeliveries(signal), `deliveries#${dataVersion}`)
  // Selected by filename, not id: a full re-ingestion rebuilds the tables, so ids change but names don't.
  const [selected, setSelected] = useState<string | null>(null)
  const selectedDelivery = data?.find((d) => d.filename === selected)

  const panelRef = useRef<HTMLDivElement>(null)
  useEffect(() => {
    if (selected) panelRef.current?.scrollIntoView({ block: 'nearest' })
  }, [selected])

  let body
  if (error) {
    body = <ErrorNotice message={errorMessage(error)} onRetry={reload} />
  } else if (!data) {
    body = <p className="muted">Loading deliveries…</p>
  } else if (data.length === 0) {
    body = (
      <EmptyState title="No deliveries ingested yet">
        <p>Run ingestion to read the delivery files and check their quality.</p>
        <button className="btn btn-primary" onClick={onRunIngestion} disabled={ingesting}>
          {ingesting ? 'Running ingestion…' : 'Run ingestion'}
        </button>
      </EmptyState>
    )
  } else {
    const count = (h: Health) => data.filter((d) => d.health === h).length
    const excluded = data.reduce((n, d) => n + d.rows_quarantined, 0)
    body = (
      <div className={loading ? 'is-updating' : undefined} aria-busy={loading}>
        <p className="health-summary">
          <span className="badge badge-fail">{count('fail')} failing</span>{' '}
          <span className="badge badge-warn">{count('warn')} with warnings</span>{' '}
          <span className="badge badge-pass">{count('pass')} passing</span>{' '}
          <span className="muted">{excluded} rows excluded from the metrics</span>
        </p>
        <DeliveryGrid deliveries={data} selected={selected} onSelect={setSelected} />
        <div ref={panelRef}>{selectedDelivery && <DeliveryDetailPanel key={selectedDelivery.filename} delivery={selectedDelivery} dataVersion={dataVersion} />}</div>
        <h2 className="section-title">All deliveries, worst first</h2>
        <DeliveryList deliveries={data} selected={selected} onSelect={setSelected} />
      </div>
    )
  }

  return (
    <>
      <h1>Data health</h1>
      {body}
    </>
  )
}
