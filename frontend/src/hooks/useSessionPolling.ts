import { useEffect, useRef, useState } from 'react'
import { fetchStatus } from '../api/client'
import type { SessionStatusResponse } from '../types'

const POLL_MS = 4000

export function useSessionPolling() {
  const [status, setStatus] = useState<SessionStatusResponse | null>(null)
  const [error, setError] = useState<string | null>(null)
  const timerRef = useRef<ReturnType<typeof setInterval> | null>(null)

  async function refresh() {
    try {
      const data = await fetchStatus()
      setStatus(data)
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

  return { status, error, refresh }
}
