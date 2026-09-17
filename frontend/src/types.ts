export type SessionStatus = 'active' | 'stopped'

export interface Session {
  id: string
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

export type MAWatchStatus = 'active' | 'stopped'
export type MARelationship = 'golden' | 'death' | null

export interface MAWatch {
  id: string
  status: MAWatchStatus
  ticker: string
  short_period: number
  long_period: number
  last_short_ma: number | null
  last_long_ma: number | null
  relationship: MARelationship
  last_checked_date: string | null
  last_alerted_at: string | null
  created_at: string
  stopped_at: string | null
  last_check_error: string | null
  market_open: boolean
}

export type ChartRange = '1W' | '1M' | '3M' | '6M' | '1Y' | '5Y'

export interface ChartPoint {
  date: string
  close: number
  short_ma: number
  long_ma: number
}

export interface MAChartData {
  ticker: string
  short_period: number
  long_period: number
  range: ChartRange
  points: ChartPoint[]
}
