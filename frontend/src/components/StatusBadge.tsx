import type { Health } from '../api/types'

const LABEL: Record<Health, string> = { pass: 'Pass', warn: 'Warning', fail: 'Fail' }

/** Color is never the only signal: the label is always spelled out. */
export default function StatusBadge({ health }: { health: Health }) {
  return <span className={`badge badge-${health}`}>{LABEL[health]}</span>
}
