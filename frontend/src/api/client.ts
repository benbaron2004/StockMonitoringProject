import type { ChartRange, MAChartData, MAWatch, Session, TickerPreset } from '../types'

async function parseOrThrow(res: Response) {
  if (!res.ok) {
    const body = await res.json().catch(() => null)
    throw new Error(body?.detail ?? `request failed with status ${res.status}`)
  }
  return res.json()
}

async function throwIfNotOk(res: Response) {
  if (!res.ok) {
    const body = await res.json().catch(() => null)
    throw new Error(body?.detail ?? `request failed with status ${res.status}`)
  }
}

export async function fetchTickers(): Promise<TickerPreset[]> {
  const res = await fetch('/api/meta/tickers')
  return parseOrThrow(res)
}

export async function fetchSessions(): Promise<Session[]> {
  const res = await fetch('/api/sessions')
  return parseOrThrow(res)
}

export async function startSession(tickerA: string, tickerB: string, thresholdPct: number): Promise<Session> {
  const res = await fetch('/api/sessions', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ ticker_a: tickerA, ticker_b: tickerB, threshold_pct: thresholdPct }),
  })
  return parseOrThrow(res)
}

export async function stopSession(id: string): Promise<Session> {
  const res = await fetch(`/api/sessions/${id}/stop`, { method: 'POST' })
  return parseOrThrow(res)
}

export async function removeSession(id: string): Promise<void> {
  // 204 No Content on success -- no body to parse, unlike the other calls.
  const res = await fetch(`/api/sessions/${id}`, { method: 'DELETE' })
  await throwIfNotOk(res)
}

export async function fetchMAWatches(): Promise<MAWatch[]> {
  const res = await fetch('/api/ma-watches')
  return parseOrThrow(res)
}

export async function startMAWatch(ticker: string, shortPeriod: number, longPeriod: number): Promise<MAWatch> {
  const res = await fetch('/api/ma-watches', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ ticker, short_period: shortPeriod, long_period: longPeriod }),
  })
  return parseOrThrow(res)
}

export async function stopMAWatch(id: string): Promise<MAWatch> {
  const res = await fetch(`/api/ma-watches/${id}/stop`, { method: 'POST' })
  return parseOrThrow(res)
}

export async function removeMAWatch(id: string): Promise<void> {
  const res = await fetch(`/api/ma-watches/${id}`, { method: 'DELETE' })
  await throwIfNotOk(res)
}

export async function fetchMAChart(
  ticker: string,
  shortPeriod: number,
  longPeriod: number,
  range: ChartRange,
  signal?: AbortSignal,
): Promise<MAChartData> {
  const params = new URLSearchParams({
    ticker,
    short_period: String(shortPeriod),
    long_period: String(longPeriod),
    range,
  })
  const res = await fetch(`/api/ma-watches/chart?${params}`, { signal })
  return parseOrThrow(res)
}
