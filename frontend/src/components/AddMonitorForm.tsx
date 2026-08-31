import { useState } from 'react'
import { startSession } from '../api/client'
import type { TickerPreset } from '../types'
import { ThresholdInput } from './ThresholdInput'
import { TickerSelector } from './TickerSelector'

const DEFAULT_THRESHOLD = 2.0

interface Props {
  tickers: TickerPreset[]
  onStarted: () => void
}

export function AddMonitorForm({ tickers, onStarted }: Props) {
  const [tickerA, setTickerA] = useState('')
  const [tickerB, setTickerB] = useState('')
  const [threshold, setThreshold] = useState(DEFAULT_THRESHOLD)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const canStart = Boolean(tickerA && tickerB && tickerA !== tickerB && threshold > 0)

  async function handleStart() {
    setBusy(true)
    setError(null)
    try {
      await startSession(tickerA, tickerB, threshold)
      setTickerA('')
      setTickerB('')
      setThreshold(DEFAULT_THRESHOLD)
      onStarted()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'failed to start monitoring')
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="add-monitor-form">
      {error && <div className="banner banner-error">{error}</div>}

      <TickerSelector
        tickers={tickers}
        tickerA={tickerA}
        tickerB={tickerB}
        onChangeA={setTickerA}
        onChangeB={setTickerB}
        disabled={busy}
      />

      <ThresholdInput value={threshold} onChange={setThreshold} disabled={busy} />

      <button className="start-button" onClick={handleStart} disabled={!canStart || busy}>
        Start Monitoring
      </button>
    </div>
  )
}
