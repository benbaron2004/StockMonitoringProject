import { useEffect, useState } from 'react'
import './App.css'
import { fetchTickers, removeMAWatch, removeSession, stopMAWatch, stopSession } from './api/client'
import { AddMAWatchForm } from './components/AddMAWatchForm'
import { AddMonitorForm } from './components/AddMonitorForm'
import { MAWatchCard } from './components/MAWatchCard'
import { MonitorCard } from './components/MonitorCard'
import { useMAWatchesPolling } from './hooks/useMAWatchesPolling'
import { useSessionsPolling } from './hooks/useSessionsPolling'
import type { TickerPreset } from './types'

function App() {
  const { sessions, error, refresh } = useSessionsPolling()
  const { watches, error: maError, refresh: refreshMA } = useMAWatchesPolling()
  const [tickers, setTickers] = useState<TickerPreset[]>([])
  const [busyIds, setBusyIds] = useState<Set<string>>(new Set())
  const [maBusyIds, setMaBusyIds] = useState<Set<string>>(new Set())
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

  function setMaBusy(id: string, busy: boolean) {
    setMaBusyIds((prev) => {
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

  async function handleStopMAWatch(id: string) {
    setMaBusy(id, true)
    setActionError(null)
    try {
      await stopMAWatch(id)
      await refreshMA()
    } catch (err) {
      setActionError(err instanceof Error ? err.message : 'failed to stop watching')
    } finally {
      setMaBusy(id, false)
    }
  }

  async function handleRemoveMAWatch(id: string) {
    setMaBusy(id, true)
    setActionError(null)
    try {
      await removeMAWatch(id)
      await refreshMA()
    } catch (err) {
      setActionError(err instanceof Error ? err.message : 'failed to remove watch')
    } finally {
      setMaBusy(id, false)
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

      <h2 className="section-heading">Moving Average Watches</h2>
      {maError && <div className="banner banner-error">Can't reach the backend: {maError}</div>}

      <AddMAWatchForm tickers={tickers} onStarted={refreshMA} />

      <div className="monitor-list">
        {watches && watches.length === 0 && (
          <p className="empty-state">No moving-average watches yet — add one above to get started.</p>
        )}
        {watches?.map((watch) => (
          <MAWatchCard
            key={watch.id}
            watch={watch}
            isBusy={maBusyIds.has(watch.id)}
            onStop={handleStopMAWatch}
            onRemove={handleRemoveMAWatch}
          />
        ))}
      </div>
    </div>
  )
}

export default App
