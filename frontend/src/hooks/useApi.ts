import { useEffect, useRef, useState } from 'react'

interface Settled<T> {
  id?: string // which request produced this result
  data?: T
  error?: unknown
}

/**
 * Fetch whenever `key` changes (or reload() is called). Guarantees:
 *  - a response for old parameters can never overwrite a newer one (requests are aborted),
 *  - previous data stays visible while refetching (no flicker), but is dropped on error
 *    so stale numbers are never shown next to a failure message.
 * `loading` is derived: true while the latest request hasn't settled. `enabled=false` skips fetching.
 */
export function useApi<T>(fetcher: (signal: AbortSignal) => Promise<T>, key: string, enabled = true) {
  const [nonce, setNonce] = useState(0)
  const [settled, setSettled] = useState<Settled<T>>({})
  const fetcherRef = useRef(fetcher)
  useEffect(() => {
    fetcherRef.current = fetcher
  })

  const requestId = `${key}#${nonce}`
  useEffect(() => {
    if (!enabled) return
    const ctrl = new AbortController()
    fetcherRef.current(ctrl.signal).then(
      (data) => setSettled({ id: requestId, data }),
      (error: unknown) => {
        if (!ctrl.signal.aborted) setSettled({ id: requestId, error })
      },
    )
    return () => ctrl.abort()
  }, [requestId, enabled])

  const current = settled.id === requestId
  return {
    data: settled.data,
    error: current ? settled.error : undefined,
    loading: enabled && !current,
    reload: () => setNonce((n) => n + 1),
  }
}
