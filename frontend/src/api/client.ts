import type { Session, TickerPreset } from '../types'

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
