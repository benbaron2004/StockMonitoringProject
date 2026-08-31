import type { Session } from '../types'

function fmtPct(value: number | null): string {
  if (value === null) return '—'
  const sign = value > 0 ? '+' : ''
  return `${sign}${value.toFixed(2)}%`
}

function fmtPrice(value: number | null): string {
  if (value === null) return '—'
  return `₪${value.toFixed(2)}`
}

function fmtTime(iso: string | null): string {
  if (!iso) return '—'
  return new Date(iso).toLocaleTimeString()
}

interface Props {
  session: Session
  isBusy: boolean
  onStop: (id: string) => void
  onRemove: (id: string) => void
}

export function MonitorCard({ session, isBusy, onStop, onRemove }: Props) {
  const overThreshold =
    session.spread_pct !== null && session.threshold_pct !== null && session.spread_pct >= session.threshold_pct

  return (
    <div className="monitor-card">
      <div className="monitor-card-header">
        {session.ticker_a} vs {session.ticker_b}
      </div>

      <div className="market-banner">
        {session.market_open ? 'TASE market is open' : 'TASE market is closed — prices will not update'}
      </div>

      <div className="stock-rows">
        <div className="stock-row">
          <span className="ticker">{session.ticker_a}</span>
          <span className="price">{fmtPrice(session.current_price_a)}</span>
          <span className="pct">{fmtPct(session.pct_change_a)}</span>
        </div>
        <div className="stock-row">
          <span className="ticker">{session.ticker_b}</span>
          <span className="price">{fmtPrice(session.current_price_b)}</span>
          <span className="pct">{fmtPct(session.pct_change_b)}</span>
        </div>
      </div>

      <div className={`spread ${overThreshold ? 'spread-over' : ''}`}>
        Spread: {session.spread_pct !== null ? session.spread_pct.toFixed(2) : '—'} pts
        <span className="threshold-note"> (threshold: {session.threshold_pct} pts)</span>
      </div>

      {session.alerted && (
        <div className="alert-badge">Alert sent{session.alerted_at ? ` at ${fmtTime(session.alerted_at)}` : ''}</div>
      )}

      {session.last_poll_error && (
        <div className="poll-error-banner">
          Could not fetch a fresh price — showing the last known values. ({session.last_poll_error})
        </div>
      )}

      <div className="meta-row">
        Last updated: {fmtTime(session.last_updated_at)} · Prices from Yahoo Finance, ~15 min delayed
      </div>

      {session.status === 'active' ? (
        <button className="stop-button" onClick={() => onStop(session.id)} disabled={isBusy}>
          Stop Monitoring
        </button>
      ) : (
        <button className="remove-button" onClick={() => onRemove(session.id)} disabled={isBusy}>
          Remove
        </button>
      )}
    </div>
  )
}
