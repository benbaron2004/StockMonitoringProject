import { useEffect } from 'react'

interface Props {
  title: string
  onClose: () => void
  children: React.ReactNode
}

// Plain fixed-position overlay, no portal -- nothing in this app's DOM tree
// applies a CSS transform to an ancestor, so `position: fixed` already
// escapes the .monitor-card boundary without needing createPortal.
export function ChartModal({ title, onClose, children }: Props) {
  useEffect(() => {
    const previousOverflow = document.body.style.overflow
    document.body.style.overflow = 'hidden'
    function handleKeyDown(e: KeyboardEvent) {
      if (e.key === 'Escape') onClose()
    }
    window.addEventListener('keydown', handleKeyDown)
    return () => {
      document.body.style.overflow = previousOverflow
      window.removeEventListener('keydown', handleKeyDown)
    }
  }, [onClose])

  return (
    <div className="chart-modal-backdrop" onClick={onClose}>
      <div
        className="chart-modal"
        role="dialog"
        aria-modal="true"
        aria-label={title}
        onClick={(e) => e.stopPropagation()}
      >
        <div className="chart-modal-header">
          <span className="chart-modal-title">{title}</span>
          <button type="button" className="chart-modal-close" onClick={onClose} aria-label="Close enlarged chart">
            ✕
          </button>
        </div>
        <div className="chart-modal-body">{children}</div>
      </div>
    </div>
  )
}
