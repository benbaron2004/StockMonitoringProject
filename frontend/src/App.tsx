import { useEffect, useState } from 'react'
import './App.css'
import { fetchTickers, removeSession, stopSession } from './api/client'
import { AddMonitorForm } from './components/AddMonitorForm'
import { MonitorCard } from './components/MonitorCard'
import { useSessionsPolling } from './hooks/useSessionsPolling'
import type { TickerPreset } from './types'

function App() {
  const { sessions, error, refresh } = useSessionsPolling()
  const [tickers, setTickers] = useState<TickerPreset[]>([])
  const [busyIds, setBusyIds] = useState<Set<string>>(new Set())
  const [actionError, setActionError] = useState<string | null>(null)

  useEffect(() => {
    fetchTickers().then(setTickers).catch(() => setActionError('Could not load the stock list.'))
  }, [])

  function setBusy(id: string, busy: boolean) {
    setBusyIds((prev) => {
      const next = new Set(prev)
      if (busy) next.add(id)
      else next.delete(id)
      return next
    })
  }

  async function handleStop(id: string) {
    setBusy(id, true)
    setActionError(null)
    try {
      await stopSession(id)
      await refresh()
    } catch (err) {
      setActionError(err instanceof Error ? err.message : 'failed to stop monitoring')
    } finally {
      setBusy(id, false)
    }
  }

  async function handleRemove(id: string) {
    setBusy(id, true)
    setActionError(null)
    try {
      await removeSession(id)
      await refresh()
    } catch (err) {
      setActionError(err instanceof Error ? err.message : 'failed to remove monitor')
    } finally {
      setBusy(id, false)
    }
  }

  return (
    <div className="app">
      <h1>TASE Spread Monitor</h1>

      {error && <div className="banner banner-error">Can't reach the backend: {error}</div>}
      {actionError && <div className="banner banner-error">{actionError}</div>}

      <AddMonitorForm tickers={tickers} onStarted={refresh} />

      <div className="monitor-list">
        {sessions && sessions.length === 0 && (
          <p className="empty-state">No stocks being monitored yet — add a pair above to get started.</p>
        )}
        {sessions?.map((session) => (
          <MonitorCard
            key={session.id}
            session={session}
            isBusy={busyIds.has(session.id)}
            onStop={handleStop}
            onRemove={handleRemove}
          />
        ))}
      </div>
    </div>
  )
}

export default App
