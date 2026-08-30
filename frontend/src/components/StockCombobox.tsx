import { useRef, useState } from 'react'
import type { TickerPreset } from '../types'

interface Props {
  tickers: TickerPreset[]
  value: string
  onChange: (symbol: string) => void
  disabled: boolean
  label: string
}

const MAX_RESULTS = 10

function filterTickers(tickers: TickerPreset[], query: string): TickerPreset[] {
  const q = query.trim().toLowerCase()
  if (!q) return []
  return tickers.filter((t) => t.symbol.toLowerCase().includes(q) || t.name.toLowerCase().includes(q))
}

export function StockCombobox({ tickers, value, onChange, disabled, label }: Props) {
  const [query, setQuery] = useState('')
  const [isOpen, setIsOpen] = useState(false)
  const inputRef = useRef<HTMLInputElement>(null)

  const selected = tickers.find((t) => t.symbol === value) ?? null
  const matches = filterTickers(tickers, query)
  const visibleMatches = matches.slice(0, MAX_RESULTS)
  const extraCount = matches.length - visibleMatches.length

  function selectTicker(symbol: string) {
    onChange(symbol)
    setQuery('')
    setIsOpen(false)
    inputRef.current?.blur()
  }

  function clearSelection() {
    onChange('')
    setQuery('')
    inputRef.current?.focus()
  }

  const displayValue = isOpen ? query : (selected ? `${selected.name} (${selected.symbol})` : '')

  return (
    <div className="combobox">
      <label>
        {label}
        <div className="combobox-input-wrap">
          <input
            ref={inputRef}
            type="text"
            value={displayValue}
            placeholder="Type a stock name or symbol…"
            disabled={disabled}
            autoComplete="off"
            onFocus={() => {
              setQuery('')
              setIsOpen(true)
            }}
            onChange={(e) => {
              setQuery(e.target.value)
              setIsOpen(true)
            }}
            onKeyDown={(e) => {
              if (e.key === 'Escape') {
                setIsOpen(false)
                inputRef.current?.blur()
              }
            }}
            onBlur={() => setIsOpen(false)}
          />
          {selected && !isOpen && !disabled && (
            <button type="button" className="combobox-clear" onClick={clearSelection} aria-label={`Clear ${label}`}>
              ×
            </button>
          )}
        </div>
      </label>

      {isOpen && (
        <ul className="combobox-results">
          {query.trim() === '' ? (
            <li className="combobox-hint">Start typing a name or symbol…</li>
          ) : visibleMatches.length === 0 ? (
            <li className="combobox-hint">No matching stocks</li>
          ) : (
            <>
              {visibleMatches.map((t) => (
                <li key={t.symbol}>
                  <button type="button" onMouseDown={(e) => e.preventDefault()} onClick={() => selectTicker(t.symbol)}>
                    {t.name} <span className="combobox-symbol">({t.symbol})</span>
                  </button>
                </li>
              ))}
              {extraCount > 0 && <li className="combobox-hint">+{extraCount} more — keep typing…</li>}
            </>
          )}
        </ul>
      )}
    </div>
  )
}
