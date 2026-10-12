import { useState } from 'react'
import { errorMessage, runIngestion } from './api/client'
import HealthView from './views/health/HealthView'
import MetricsView from './views/metrics/MetricsView'

type View = 'metrics' | 'health'
const TABS: { id: View; label: string }[] = [
  { id: 'metrics', label: 'Campaign metrics' },
  { id: 'health', label: 'Data health' },
]

interface IngestState {
  running: boolean
  message?: string
  failed?: boolean
}

export default function App() {
  const [view, setView] = useState<View>('metrics')
  const [dataVersion, setDataVersion] = useState(0) // bumps after each ingestion so every view refetches
  const [ingest, setIngest] = useState<IngestState>({ running: false })

  async function run() {
    setIngest({ running: true })
    try {
      const r = await runIngestion()
      const c = r.health_counts
      const summary = `${c.pass ?? 0} passing, ${c.warn ?? 0} with warnings, ${c.fail ?? 0} failing`
      const failed = r.errors.length > 0
      setIngest({ running: false, failed, message: failed ? `Finished with ${r.errors.length} write errors. ${summary}.` : `Ingestion finished: ${summary}.` })
      setDataVersion((v) => v + 1)
    } catch (err) {
      setIngest({ running: false, message: errorMessage(err), failed: true })
    }
  }

  const viewProps = { dataVersion, ingesting: ingest.running, onRunIngestion: run }
  return (
    <>
      <header className="topbar">
        <strong className="brand">Campaign Data Hub</strong>
        <nav aria-label="Views">
          {TABS.map((t) => (
            <button key={t.id} className="tab" aria-current={view === t.id ? 'page' : undefined} onClick={() => setView(t.id)}>
              {t.label}
            </button>
          ))}
        </nav>
        <div className="topbar-actions">
          <span className={ingest.failed ? 'status status-bad' : 'status'} role="status">
            {ingest.message}
          </span>
          <button className="btn btn-primary" onClick={run} disabled={ingest.running}>
            {ingest.running ? 'Running ingestion…' : 'Run ingestion'}
          </button>
        </div>
      </header>
      {/* Both views stay mounted so filters and selections survive switching tabs. */}
      <main>
        <div hidden={view !== 'metrics'}>
          <MetricsView {...viewProps} />
        </div>
        <div hidden={view !== 'health'}>
          <HealthView {...viewProps} />
        </div>
      </main>
    </>
  )
}
