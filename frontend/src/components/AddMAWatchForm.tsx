import { useState } from 'react'
import { startMAWatch } from '../api/client'
import type { TickerPreset } from '../types'
import { MAChart } from './MAChart'
import { StockCombobox } from './StockCombobox'

const DEFAULT_SHORT_PERIOD = 5
const DEFAULT_LONG_PERIOD = 13

interface Props {
  tickers: TickerPreset[]
  onStarted: () => void
}

export function AddMAWatchForm({ tickers, onStarted }: Props) {
  const [ticker, setTicker] = useState('')
  const [shortPeriod, setShortPeriod] = useState(DEFAULT_SHORT_PERIOD)
  const [longPeriod, setLongPeriod] = useState(DEFAULT_LONG_PERIOD)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const canStart = Boolean(ticker && shortPeriod > 0 && longPeriod > 0 && shortPeriod < longPeriod)

  async function handleStart() {
    setBusy(true)
    setError(null)
    try {
      await startMAWatch(ticker, shortPeriod, longPeriod)
      setTicker('')
      setShortPeriod(DEFAULT_SHORT_PERIOD)
      setLongPeriod(DEFAULT_LONG_PERIOD)
      onStarted()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'failed to start watching')
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="add-monitor-form">
      {error && <div className="banner banner-error">{error}</div>}

      <StockCombobox tickers={tickers} value={ticker} onChange={setTicker} disabled={busy} label="Stock" />

      <div className="ticker-selector-row">
        <label className="threshold-input">
          Short period (days)
          <input
            type="number"
            min={1}
            step={1}
            value={shortPeriod}
            onChange={(e) => setShortPeriod(Number(e.target.value))}
            disabled={busy}
          />
        </label>
        <label className="threshold-input">
          Long period (days)
          <input
            type="number"
            min={1}
            step={1}
            value={longPeriod}
            onChange={(e) => setLongPeriod(Number(e.target.value))}
            disabled={busy}
          />
        </label>
      </div>

      {shortPeriod >= longPeriod && (
        <p className="field-error">Short period must be less than long period.</p>
      )}

      {canStart && <MAChart ticker={ticker} shortPeriod={shortPeriod} longPeriod={longPeriod} />}

      <button className="start-button" onClick={handleStart} disabled={!canStart || busy}>
        Start Watching
      </button>
    </div>
  )
}
