interface Props {
  canStart: boolean
  isActive: boolean
  isBusy: boolean
  onStart: () => void
  onStop: () => void
}

export function SessionControls({ canStart, isActive, isBusy, onStart, onStop }: Props) {
  if (isActive) {
    return (
      <button className="stop-button" onClick={onStop} disabled={isBusy}>
        Stop Monitoring
      </button>
    )
  }
  return (
    <button className="start-button" onClick={onStart} disabled={!canStart || isBusy}>
      Start Monitoring
    </button>
  )
}
