import type { MAWatch } from '../types'
import { MAChart } from './MAChart'

function fmtValue(value: number | null): string {
  if (value === null) return '—'
  return value.toFixed(2)
}

function fmtDate(iso: string | null): string {
  if (!iso) return '—'
  return new Date(iso).toLocaleDateString()
}

interface Props {
  watch: MAWatch
  isBusy: boolean
  onStop: (id: string) => void
  onRemove: (id: string) => void
}

export function MAWatchCard({ watch, isBusy, onStop, onRemove }: Props) {
  const relationshipLabel =
    watch.relationship === 'golden' ? 'Golden (short above long)' : watch.relationship === 'death' ? 'Death (short below long)' : 'Not checked yet'

  return (
    <div className="monitor-card">
      <div className="monitor-card-header">
        {watch.ticker} — {watch.short_period}/{watch.long_period}-day SMA
      </div>

      <div className="market-banner">
        {watch.market_open ? 'TASE market is open' : 'TASE market is closed'}
      </div>

      <div className="stock-rows">
        <div className="stock-row">
          <span className="ticker">{watch.short_period}-day SMA</span>
          <span className="price">{fmtValue(watch.last_short_ma)}</span>
        </div>
        <div className="stock-row">
          <span className="ticker">{watch.long_period}-day SMA</span>
          <span className="price">{fmtValue(watch.last_long_ma)}</span>
        </div>
      </div>

      <div className={`spread ${watch.relationship === 'golden' ? 'spread-over' : ''}`}>{relationshipLabel}</div>

      {watch.last_alerted_at && <div className="alert-badge">Alert sent {fmtDate(watch.last_alerted_at)}</div>}

      {watch.last_check_error && (
        <div className="poll-error-banner">Could not check today yet. ({watch.last_check_error})</div>
      )}

      <div className="meta-row">
        Last checked: {fmtDate(watch.last_checked_date)} · Checked once daily after TASE close, re-alerts on every new crossover
      </div>

      {/* Primitive props, deliberately not `watch={watch}` -- see MAChart.tsx's
          comment: polling returns a fresh object every ~4s even when nothing
          changed, which would refetch the chart forever if keyed on the object. */}
      <MAChart ticker={watch.ticker} shortPeriod={watch.short_period} longPeriod={watch.long_period} />

      {watch.status === 'active' ? (
        <button className="stop-button" onClick={() => onStop(watch.id)} disabled={isBusy}>
          Stop Watching
        </button>
      ) : (
        <button className="remove-button" onClick={() => onRemove(watch.id)} disabled={isBusy}>
          Remove
        </button>
      )}
    </div>
  )
}
