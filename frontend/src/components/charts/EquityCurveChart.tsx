import type { EquityPoint } from '../../api'
import { formatMoney } from '../../lib/money'

/** Equity over time as an SVG line chart with labelled axes (USD vs UTC date). */
export interface EquityCurveChartProps {
  points: EquityPoint[]
  title?: string
}

const W = 720
const H = 280
const PAD = { top: 12, right: 40, bottom: 44, left: 104 }
const Y_TICKS = 4
const X_TICKS = 4

export function EquityCurveChart({ points, title = 'Equity curve' }: EquityCurveChartProps) {
  if (points.length === 0) {
    return <div className="equity-curve-chart equity-curve-chart--empty">No equity data yet.</div>
  }

  // Floats are fine here: plot coordinates only.
  const values = points.map((p) => Number(p.equity))
  const times = points.map((p) => Date.parse(p.timestamp))
  const minV = Math.min(...values)
  const maxV = Math.max(...values)
  const minT = times[0]
  const maxT = times[times.length - 1]
  const vSpan = maxV - minV || 1
  const tSpan = maxT - minT || 1
  const innerW = W - PAD.left - PAD.right
  const innerH = H - PAD.top - PAD.bottom
  const x = (t: number) => PAD.left + ((t - minT) / tSpan) * innerW
  const y = (v: number) => PAD.top + (1 - (v - minV) / vSpan) * innerH

  const path = points
    .map((_, i) => `${i === 0 ? 'M' : 'L'}${x(times[i]).toFixed(1)},${y(values[i]).toFixed(1)}`)
    .join(' ')
  const yTicks = Array.from({ length: Y_TICKS + 1 }, (_, i) => minV + (vSpan * i) / Y_TICKS)
  const xTicks = Array.from({ length: X_TICKS + 1 }, (_, i) => minT + (tSpan * i) / X_TICKS)

  return (
    <figure className="equity-curve-chart">
      <svg viewBox={`0 0 ${W} ${H}`} role="img" aria-label={title}>
        {yTicks.map((v) => (
          <g key={v}>
            <line className="chart-grid" x1={PAD.left} x2={W - PAD.right} y1={y(v)} y2={y(v)} />
            <text className="chart-tick" x={PAD.left - 8} y={y(v)} textAnchor="end" dy="0.32em">
              {formatMoney(v.toFixed(2))}
            </text>
          </g>
        ))}
        {xTicks.map((t) => (
          <text key={t} className="chart-tick" x={x(t)} y={H - PAD.bottom + 16} textAnchor="middle">
            {new Date(t).toISOString().slice(0, 10)}
          </text>
        ))}
        <path className="chart-line" d={path} fill="none" />
        <text className="chart-label" x={PAD.left + innerW / 2} y={H - 6} textAnchor="middle">
          Date (UTC)
        </text>
        <text
          className="chart-label"
          transform={`translate(14 ${PAD.top + innerH / 2}) rotate(-90)`}
          textAnchor="middle"
        >
          Equity (USD)
        </text>
      </svg>
    </figure>
  )
}
