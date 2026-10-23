/**
 * Placeholder for the open-positions table shown on the Positions page.
 * Wired to real data once backend/app/api/ exposes a positions endpoint.
 */
export interface PositionRow {
  symbol: string
  quantity: number
}

export function PositionsTable({ rows }: { rows: PositionRow[] }) {
  return (
    <table className="positions-table">
      <thead>
        <tr>
          <th>Symbol</th>
          <th>Quantity</th>
        </tr>
      </thead>
      <tbody>
        {rows.map((row) => (
          <tr key={row.symbol}>
            <td>{row.symbol}</td>
            <td>{row.quantity}</td>
          </tr>
        ))}
      </tbody>
    </table>
  )
}
