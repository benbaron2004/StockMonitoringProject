interface Props {
  value: number
  onChange: (value: number) => void
  disabled: boolean
}

export function ThresholdInput({ value, onChange, disabled }: Props) {
  return (
    <label className="threshold-input">
      Alert threshold (percentage points)
      <input
        type="number"
        min={0.1}
        step={0.1}
        value={value}
        onChange={(e) => onChange(Number(e.target.value))}
        disabled={disabled}
      />
    </label>
  )
}
