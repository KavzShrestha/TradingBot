/** Small stat tile used on the Overview and Strategy detail pages. */
export interface MetricCardProps {
  label: string
  value: string
}

export function MetricCard({ label, value }: MetricCardProps) {
  return (
    <div className="metric-card">
      <span className="metric-card__label">{label}</span>
      <span className="metric-card__value">{value}</span>
    </div>
  )
}
