import { useEffect, useState } from 'react'
import './App.css'
import { fetchTickers, startSession, stopSession } from './api/client'
import { LiveStatus } from './components/LiveStatus'
import { SessionControls } from './components/SessionControls'
import { ThresholdInput } from './components/ThresholdInput'
import { TickerSelector } from './components/TickerSelector'
import { useSessionPolling } from './hooks/useSessionPolling'
import type { TickerPreset } from './types'

const DEFAULT_THRESHOLD = 2.0

function App() {
  const { status, error, refresh } = useSessionPolling()
  const [tickers, setTickers] = useState<TickerPreset[]>([])
  const [tickerA, setTickerA] = useState('')
  const [tickerB, setTickerB] = useState('')
  const [threshold, setThreshold] = useState(DEFAULT_THRESHOLD)
  const [busy, setBusy] = useState(false)
  const [actionError, setActionError] = useState<string | null>(null)

  useEffect(() => {
    fetchTickers().then(setTickers).catch(() => setActionError('Could not load the stock list.'))
  }, [])

  const isActive = status?.status === 'active'
  const canStart = Boolean(tickerA && tickerB && tickerA !== tickerB && threshold > 0)

  async function handleStart() {
    setBusy(true)
    setActionError(null)
    try {
      await startSession(tickerA, tickerB, threshold)
      await refresh()
    } catch (err) {
      setActionError(err instanceof Error ? err.message : 'failed to start monitoring')
    } finally {
      setBusy(false)
    }
  }

  async function handleStop() {
    setBusy(true)
    setActionError(null)
    try {
      await stopSession()
      await refresh()
    } catch (err) {
      setActionError(err instanceof Error ? err.message : 'failed to stop monitoring')
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="app">
      <h1>TASE Spread Monitor</h1>

      {error && <div className="banner banner-error">Can't reach the backend: {error}</div>}
      {actionError && <div className="banner banner-error">{actionError}</div>}

      <TickerSelector
        tickers={tickers}
        tickerA={tickerA}
        tickerB={tickerB}
        onChangeA={setTickerA}
        onChangeB={setTickerB}
        disabled={isActive}
      />

      <ThresholdInput value={threshold} onChange={setThreshold} disabled={isActive} />

      <SessionControls canStart={canStart} isActive={isActive} isBusy={busy} onStart={handleStart} onStop={handleStop} />

      {status && status.status !== 'idle' && <LiveStatus status={status} />}
    </div>
  )
}

export default App
