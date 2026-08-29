import type { SessionStatusResponse } from '../types'

function fmtPct(value: number | null): string {
  if (value === null) return '—'
  const sign = value > 0 ? '+' : ''
  return `${sign}${value.toFixed(2)}%`
}

function fmtTime(iso: string | null): string {
  if (!iso) return '—'
  return new Date(iso).toLocaleTimeString()
}

export function LiveStatus({ status }: { status: SessionStatusResponse }) {
  const overThreshold =
    status.spread_pct !== null && status.threshold_pct !== null && status.spread_pct >= status.threshold_pct

  return (
    <div className="live-status">
      <div className="market-banner">
        {status.market_open ? 'TASE market is open' : 'TASE market is closed — prices will not update'}
      </div>

      <div className="stock-rows">
        <div className="stock-row">
          <span className="ticker">{status.ticker_a}</span>
          <span className="pct">{fmtPct(status.pct_change_a)}</span>
        </div>
        <div className="stock-row">
          <span className="ticker">{status.ticker_b}</span>
          <span className="pct">{fmtPct(status.pct_change_b)}</span>
        </div>
      </div>

      <div className={`spread ${overThreshold ? 'spread-over' : ''}`}>
        Spread: {status.spread_pct !== null ? status.spread_pct.toFixed(2) : '—'} pts
        <span className="threshold-note"> (threshold: {status.threshold_pct} pts)</span>
      </div>

      {status.alerted && <div className="alert-badge">Alert sent{status.alerted_at ? ` at ${fmtTime(status.alerted_at)}` : ''}</div>}

      {status.last_poll_error && (
        <div className="poll-error-banner">
          Could not fetch a fresh price — showing the last known values. ({status.last_poll_error})
        </div>
      )}

      <div className="meta-row">
        Last updated: {fmtTime(status.last_updated_at)} · Prices from Yahoo Finance, ~15 min delayed
      </div>
    </div>
  )
}
