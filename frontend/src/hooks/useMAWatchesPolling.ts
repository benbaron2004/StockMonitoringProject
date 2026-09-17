import { useEffect, useRef, useState } from 'react'
import { fetchMAWatches } from '../api/client'
import type { MAWatch } from '../types'

// MA watches update at most once a day, but polling at the same cadence as
// sessions keeps the pattern identical and the cost is negligible.
const POLL_MS = 4000

export function useMAWatchesPolling() {
  const [watches, setWatches] = useState<MAWatch[] | null>(null)
  const [error, setError] = useState<string | null>(null)
  const timerRef = useRef<ReturnType<typeof setInterval> | null>(null)

  async function refresh() {
    try {
      const data = await fetchMAWatches()
      setWatches(data)
      setError(null)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'failed to reach the backend')
    }
  }

  useEffect(() => {
    refresh()
    timerRef.current = setInterval(refresh, POLL_MS)
    return () => {
      if (timerRef.current) clearInterval(timerRef.current)
    }
  }, [])

  return { watches, error, refresh }
}
