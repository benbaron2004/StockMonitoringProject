import { useRef, useState } from 'react'
import type { ChartPoint } from '../types'

// Validated categorical palette (all-pairs safe, light surface) -- see
// node scripts/validate_palette.js in the dataviz skill. Aqua sits under
// 3:1 contrast on a light surface, so it's used for the stroke/swatch only,
// never as text color -- text below always stays in normal ink.
const COLOR_CLOSE = '#2a78d6'
const COLOR_SHORT = '#eb6834'
const COLOR_LONG = '#1baf7a'

const VIEW_WIDTH = 600
const VIEW_HEIGHT = 260
const MARGIN = { top: 12, right: 12, bottom: 26, left: 48 }
const INNER_WIDTH = VIEW_WIDTH - MARGIN.left - MARGIN.right
const INNER_HEIGHT = VIEW_HEIGHT - MARGIN.top - MARGIN.bottom
const Y_TICKS = 4
const X_TICKS = 5

interface Props {
  points: ChartPoint[]
  shortPeriod: number
  longPeriod: number
}

function fmtDate(iso: string): string {
  return new Date(iso).toLocaleDateString(undefined, { month: 'short', day: 'numeric' })
}

function fmtValue(v: number): string {
  // Defensive: the API contract guarantees a finite number here, but a
  // malformed/cached response should degrade to a dash, never crash the
  // whole chart -- a hovered point is the one place a bad value would
  // otherwise reach .toFixed() and throw, taking down the entire page
  // (no error boundary is set up in this app).
  if (typeof v !== 'number' || Number.isNaN(v)) return '—'
  return `₪${v.toFixed(2)}`
}

export function MAChartSvg({ points, shortPeriod, longPeriod }: Props) {
  const svgRef = useRef<SVGSVGElement>(null)
  const [hoverIndex, setHoverIndex] = useState<number | null>(null)

  if (points.length < 2) {
    return <p className="empty-state">Not enough data to draw a chart.</p>
  }

  const allValues = points.flatMap((p) => [p.close, p.short_ma, p.long_ma])
  const rawMin = Math.min(...allValues)
  const rawMax = Math.max(...allValues)
  const pad = (rawMax - rawMin) * 0.05 || 1
  const domainMin = rawMin - pad
  const domainMax = rawMax + pad

  function x(i: number): number {
    return MARGIN.left + (i / (points.length - 1)) * INNER_WIDTH
  }
  function y(value: number): number {
    return MARGIN.top + INNER_HEIGHT - ((value - domainMin) / (domainMax - domainMin)) * INNER_HEIGHT
  }

  function buildPath(key: 'close' | 'short_ma' | 'long_ma'): string {
    return points.map((p, i) => `${i === 0 ? 'M' : 'L'} ${x(i).toFixed(2)} ${y(p[key]).toFixed(2)}`).join(' ')
  }

  const yTickValues = Array.from({ length: Y_TICKS + 1 }, (_, i) => domainMin + (i / Y_TICKS) * (domainMax - domainMin))
  const xTickIndices = Array.from({ length: X_TICKS }, (_, i) => Math.round((i / (X_TICKS - 1)) * (points.length - 1)))

  function handlePointerMove(e: React.PointerEvent<SVGRectElement>) {
    const svg = svgRef.current
    if (!svg) return
    const rect = svg.getBoundingClientRect()
    const fracX = (e.clientX - rect.left) / rect.width
    const logicalX = fracX * VIEW_WIDTH
    const t = (logicalX - MARGIN.left) / INNER_WIDTH
    const idx = Math.round(t * (points.length - 1))
    setHoverIndex(Math.max(0, Math.min(points.length - 1, idx)))
  }

  const hovered = hoverIndex !== null ? points[hoverIndex] : null
  const rawLeftPct = hoverIndex !== null ? (x(hoverIndex) / VIEW_WIDTH) * 100 : 0
  // Clamped, not switched to right-anchored -- avoids fighting the CSS
  // translateX(-50%) centering with a second, incompatible positioning mode.
  const tooltipLeftPct = Math.min(85, Math.max(15, rawLeftPct))

  return (
    <div className="ma-chart-wrap">
      <svg
        ref={svgRef}
        viewBox={`0 0 ${VIEW_WIDTH} ${VIEW_HEIGHT}`}
        className="ma-chart-svg"
        role="img"
        aria-label="Historical closing price with short and long moving averages"
      >
        {yTickValues.map((v, i) => (
          <g key={i}>
            <line x1={MARGIN.left} x2={VIEW_WIDTH - MARGIN.right} y1={y(v)} y2={y(v)} className="chart-gridline" />
            <text x={MARGIN.left - 6} y={y(v)} className="chart-axis-label" textAnchor="end" dominantBaseline="middle">
              {v.toFixed(0)}
            </text>
          </g>
        ))}

        {xTickIndices.map((i) => (
          <text key={i} x={x(i)} y={VIEW_HEIGHT - 6} className="chart-axis-label" textAnchor="middle">
            {fmtDate(points[i].date)}
          </text>
        ))}

        <path d={buildPath('close')} className="chart-line" stroke={COLOR_CLOSE} />
        <path d={buildPath('short_ma')} className="chart-line" stroke={COLOR_SHORT} />
        <path d={buildPath('long_ma')} className="chart-line" stroke={COLOR_LONG} />

        {hovered && (
          <line
            x1={x(hoverIndex!)}
            x2={x(hoverIndex!)}
            y1={MARGIN.top}
            y2={VIEW_HEIGHT - MARGIN.bottom}
            className="chart-crosshair"
          />
        )}

        <rect
          x={MARGIN.left}
          y={MARGIN.top}
          width={INNER_WIDTH}
          height={INNER_HEIGHT}
          fill="transparent"
          onPointerMove={handlePointerMove}
          onPointerLeave={() => setHoverIndex(null)}
        />
      </svg>

      {hovered && (
        <div className="chart-tooltip" style={{ left: `${tooltipLeftPct}%` }}>
          <div className="chart-tooltip-date">{fmtDate(hovered.date)}</div>
          <div className="chart-tooltip-row">
            <span className="chart-swatch" style={{ background: COLOR_CLOSE }} />
            Close <strong>{fmtValue(hovered.close)}</strong>
          </div>
          <div className="chart-tooltip-row">
            <span className="chart-swatch" style={{ background: COLOR_SHORT }} />
            {shortPeriod}-day SMA <strong>{fmtValue(hovered.short_ma)}</strong>
          </div>
          <div className="chart-tooltip-row">
            <span className="chart-swatch" style={{ background: COLOR_LONG }} />
            {longPeriod}-day SMA <strong>{fmtValue(hovered.long_ma)}</strong>
          </div>
        </div>
      )}

      <div className="chart-legend">
        <span className="chart-legend-item">
          <span className="chart-swatch" style={{ background: COLOR_CLOSE }} /> Close
        </span>
        <span className="chart-legend-item">
          <span className="chart-swatch" style={{ background: COLOR_SHORT }} /> {shortPeriod}-day SMA
        </span>
        <span className="chart-legend-item">
          <span className="chart-swatch" style={{ background: COLOR_LONG }} /> {longPeriod}-day SMA
        </span>
      </div>
    </div>
  )
}
