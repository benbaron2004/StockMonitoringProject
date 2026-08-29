export type SessionStatus = 'idle' | 'active' | 'stopped'

export interface SessionStatusResponse {
  status: SessionStatus
  ticker_a: string | null
  ticker_b: string | null
  baseline_price_a: number | null
  baseline_price_b: number | null
  current_price_a: number | null
  current_price_b: number | null
  pct_change_a: number | null
  pct_change_b: number | null
  spread_pct: number | null
  threshold_pct: number | null
  alerted: boolean
  alerted_at: string | null
  started_at: string | null
  stopped_at: string | null
  last_updated_at: string | null
  market_open: boolean
  last_poll_error: string | null
}

export interface TickerPreset {
  symbol: string
  name: string
}
