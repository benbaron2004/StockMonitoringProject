import type { ChartRange } from '../types'

const RANGES: ChartRange[] = ['1W', '1M', '3M', '6M', '1Y', '5Y']

interface Props {
  range: ChartRange
  onChange: (range: ChartRange) => void
  disabled?: boolean
}

export function ChartRangeSelector({ range, onChange, disabled }: Props) {
  return (
    <div className="chart-range-selector">
      {RANGES.map((r) => (
        <button
          key={r}
          type="button"
          className={`chart-range-button ${r === range ? 'chart-range-button-active' : ''}`}
          onClick={() => onChange(r)}
          disabled={disabled}
        >
          {r}
        </button>
      ))}
    </div>
  )
}
