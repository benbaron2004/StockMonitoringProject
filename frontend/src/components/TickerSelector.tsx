import type { TickerPreset } from '../types'

interface Props {
  tickers: TickerPreset[]
  tickerA: string
  tickerB: string
  onChangeA: (symbol: string) => void
  onChangeB: (symbol: string) => void
  disabled: boolean
}

export function TickerSelector({ tickers, tickerA, tickerB, onChangeA, onChangeB, disabled }: Props) {
  return (
    <div className="ticker-selector">
      <label>
        Stock A
        <select value={tickerA} onChange={(e) => onChangeA(e.target.value)} disabled={disabled}>
          <option value="">Select a stock…</option>
          {tickers.map((t) => (
            <option key={t.symbol} value={t.symbol}>
              {t.name} ({t.symbol})
            </option>
          ))}
        </select>
      </label>
      <label>
        Stock B
        <select value={tickerB} onChange={(e) => onChangeB(e.target.value)} disabled={disabled}>
          <option value="">Select a stock…</option>
          {tickers.map((t) => (
            <option key={t.symbol} value={t.symbol}>
              {t.name} ({t.symbol})
            </option>
          ))}
        </select>
      </label>
      {tickerA && tickerB && tickerA === tickerB && (
        <p className="field-error">Stock A and Stock B must be different.</p>
      )}
    </div>
  )
}
