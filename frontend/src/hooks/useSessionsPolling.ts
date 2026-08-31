import { useEffect, useRef, useState } from 'react'
import { fetchSessions } from '../api/client'
import type { Session } from '../types'

const POLL_MS = 4000

export function useSessionsPolling() {
  const [sessions, setSessions] = useState<Session[] | null>(null)
  const [error, setError] = useState<string | null>(null)
  const timerRef = useRef<ReturnType<typeof setInterval> | null>(null)

  async function refresh() {
    try {
      const data = await fetchSessions()
      setSessions(data)
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

  return { sessions, error, refresh }
}
