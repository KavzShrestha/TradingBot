import { PositionsTable } from '../components/tables/PositionsTable'

/** Positions page: current open positions across all strategies. */
export function Positions() {
  return (
    <main>
      <h1>Positions</h1>
      <PositionsTable rows={[]} />
    </main>
  )
}
