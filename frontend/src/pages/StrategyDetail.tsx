import { EquityCurveChart } from '../components/charts/EquityCurveChart'

/** Strategy detail page: equity curve, drawdown, metrics table, trades. */
export function StrategyDetail() {
  return (
    <main>
      <h1>Strategy detail</h1>
      <EquityCurveChart points={[]} />
    </main>
  )
}
