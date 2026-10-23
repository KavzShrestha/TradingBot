/**
 * Placeholder for the equity curve chart shown on the Overview and
 * Strategy detail pages. Real charting (equity, drawdown) lands with M6.
 */
export interface EquityCurveChartProps {
  points: { timestamp: string; equity: number }[]
}

export function EquityCurveChart({ points }: EquityCurveChartProps) {
  return <div className="equity-curve-chart">{points.length} points (chart coming in M6)</div>
}
