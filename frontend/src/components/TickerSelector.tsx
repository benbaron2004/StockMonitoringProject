import { StockCombobox } from './StockCombobox'
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
      <div className="ticker-selector-row">
        <StockCombobox tickers={tickers} value={tickerA} onChange={onChangeA} disabled={disabled} label="Stock A" />
        <StockCombobox tickers={tickers} value={tickerB} onChange={onChangeB} disabled={disabled} label="Stock B" />
      </div>
      {tickerA && tickerB && tickerA === tickerB && (
        <p className="field-error">Stock A and Stock B must be different.</p>
      )}
    </div>
  )
}
