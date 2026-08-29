import type { SessionStatusResponse, TickerPreset } from '../types'

async function parseOrThrow(res: Response) {
  if (!res.ok) {
    const body = await res.json().catch(() => null)
    throw new Error(body?.detail ?? `request failed with status ${res.status}`)
  }
  return res.json()
}

export async function fetchTickers(): Promise<TickerPreset[]> {
  const res = await fetch('/api/meta/tickers')
  return parseOrThrow(res)
}

export async function fetchStatus(): Promise<SessionStatusResponse> {
  const res = await fetch('/api/session/status')
  return parseOrThrow(res)
}

export async function startSession(
  tickerA: string,
  tickerB: string,
  thresholdPct: number,
): Promise<SessionStatusResponse> {
  const res = await fetch('/api/session/start', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ ticker_a: tickerA, ticker_b: tickerB, threshold_pct: thresholdPct }),
  })
  return parseOrThrow(res)
}

export async function stopSession(): Promise<SessionStatusResponse> {
  const res = await fetch('/api/session/stop', { method: 'POST' })
  return parseOrThrow(res)
}
