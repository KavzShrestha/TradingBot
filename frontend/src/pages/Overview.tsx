import { MetricCard } from '../components/MetricCard'

/**
 * Overview page: total equity, P&L today, per-strategy cards.
 * Placeholder metrics until backend/app/api/ and M6 wire up real data.
 */
export function Overview() {
  return (
    <main>
      <h1>Overview</h1>
      <p>Paper trading dashboard scaffold. Live metrics land in M6.</p>
      <div className="metric-card-row">
        <MetricCard label="Total equity" value="—" />
        <MetricCard label="P&L today" value="—" />
      </div>
    </main>
  )
}
