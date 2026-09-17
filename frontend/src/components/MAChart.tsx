import { useEffect, useState } from 'react'
import { fetchMAChart } from '../api/client'
import type { ChartRange, MAChartData } from '../types'
import { ChartModal } from './ChartModal'
import { ChartRangeSelector } from './ChartRangeSelector'
import { MAChartSvg } from './MAChartSvg'

const DEBOUNCE_MS = 400
const RANGE_STORAGE_KEY = 'ma-chart-range'
const VALID_RANGES: readonly ChartRange[] = ['1W', '1M', '3M', '6M', '1Y', '5Y']

// One shared preference across every chart on the page (the create-watch
// preview and every watch card), not per-watch -- "show me 1Y until I change
// it" is a single sticky default, not something to track separately per
// stock. localStorage is per-browser only, never sent to the backend.
function loadStoredRange(): ChartRange {
  try {
    const stored = localStorage.getItem(RANGE_STORAGE_KEY)
    if (stored && (VALID_RANGES as readonly string[]).includes(stored)) return stored as ChartRange
  } catch {
    // localStorage unavailable (private browsing, disabled, etc.) -- fall back below.
  }
  return '3M'
}

function storeRange(range: ChartRange) {
  try {
    localStorage.setItem(RANGE_STORAGE_KEY, range)
  } catch {
    // not critical if the preference can't be persisted
  }
}

function useDebounced<T>(value: T, delayMs: number): T {
  const [debounced, setDebounced] = useState(value)
  useEffect(() => {
    const timer = setTimeout(() => setDebounced(value), delayMs)
    return () => clearTimeout(timer)
  }, [value, delayMs])
  return debounced
}

interface Props {
  ticker: string
  shortPeriod: number
  longPeriod: number
}

// IMPORTANT: this component must be driven by primitive ticker/shortPeriod/
// longPeriod values, never a whole `watch`/form object -- useMAWatchesPolling
// returns a fresh object reference on every ~4s poll tick even when nothing
// changed, so keying the fetch effect off an object would refetch forever.
export function MAChart({ ticker, shortPeriod, longPeriod }: Props) {
  const [range, setRangeState] = useState<ChartRange>(loadStoredRange)
  function setRange(newRange: ChartRange) {
    setRangeState(newRange)
    storeRange(newRange)
  }
  const debouncedShort = useDebounced(shortPeriod, DEBOUNCE_MS)
  const debouncedLong = useDebounced(longPeriod, DEBOUNCE_MS)

  const [data, setData] = useState<MAChartData | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [isExpanded, setIsExpanded] = useState(false)

  const isValid = Boolean(ticker) && debouncedShort > 0 && debouncedLong > 0 && debouncedShort < debouncedLong

  useEffect(() => {
    if (!isValid) return
    const controller = new AbortController()
    setLoading(true)
    setError(null)
    fetchMAChart(ticker, debouncedShort, debouncedLong, range, controller.signal)
      .then((result) => {
        setData(result)
        setLoading(false)
      })
      .catch((err) => {
        if (controller.signal.aborted) return
        setError(err instanceof Error ? err.message : 'failed to load chart')
        setLoading(false)
      })
    return () => controller.abort()
  }, [ticker, debouncedShort, debouncedLong, range, isValid])

  if (!ticker || shortPeriod <= 0 || longPeriod <= 0 || shortPeriod >= longPeriod) {
    return null
  }

  function openExpanded() {
    if (data) setIsExpanded(true)
  }

  function handleExpandKeyDown(e: React.KeyboardEvent) {
    if (e.key === 'Enter' || e.key === ' ') {
      e.preventDefault()
      openExpanded()
    }
  }

  return (
    <div className="ma-chart">
      <ChartRangeSelector range={range} onChange={setRange} disabled={loading && !data} />

      {error && <div className="poll-error-banner">Could not load the chart. ({error})</div>}

      {data && (
        <div
          className="ma-chart-clickable"
          style={{ opacity: loading ? 0.5 : 1, transition: 'opacity 150ms' }}
          role="button"
          tabIndex={0}
          aria-label="Expand chart"
          onClick={openExpanded}
          onKeyDown={handleExpandKeyDown}
        >
          <MAChartSvg points={data.points} shortPeriod={data.short_period} longPeriod={data.long_period} />
          <span className="ma-chart-expand-hint">⤢ Expand</span>
        </div>
      )}

      {!data && loading && <p className="empty-state">Loading chart…</p>}

      {isExpanded && data && (
        <ChartModal title={`${ticker} — ${data.short_period}/${data.long_period}-day SMA`} onClose={() => setIsExpanded(false)}>
          <ChartRangeSelector range={range} onChange={setRange} disabled={loading && !data} />
          <div style={{ opacity: loading ? 0.5 : 1, transition: 'opacity 150ms' }}>
            <MAChartSvg points={data.points} shortPeriod={data.short_period} longPeriod={data.long_period} />
          </div>
        </ChartModal>
      )}
    </div>
  )
}
