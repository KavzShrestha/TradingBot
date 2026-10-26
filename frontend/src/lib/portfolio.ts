import type { EquityPoint, Money } from '../api'
import { subtractMoney, sumMoney } from './money'

/**
 * Sum several strategies' equity curves into one (display aggregation only).
 * A strategy with no point at a timestamp carries its previous value forward;
 * timestamps before a strategy's first point exclude it.
 */
export function combineEquityCurves(curves: EquityPoint[][]): EquityPoint[] {
  const timestamps = [...new Set(curves.flat().map((p) => p.timestamp))].sort()
  const cursors = curves.map(() => 0)
  const last: (Money | null)[] = curves.map(() => null)
  return timestamps.map((timestamp) => {
    curves.forEach((curve, i) => {
      while (cursors[i] < curve.length && curve[cursors[i]].timestamp <= timestamp) {
        last[i] = curve[cursors[i]].equity
        cursors[i]++
      }
    })
    return { timestamp, equity: sumMoney(last.filter((v): v is Money => v !== null)) }
  })
}

/** Change in equity since the last point before the latest point's UTC day. */
export function pnlToday(curve: EquityPoint[]): Money {
  if (curve.length === 0) return '0.00'
  const latest = curve[curve.length - 1]
  const day = latest.timestamp.slice(0, 10)
  const prior = [...curve].reverse().find((p) => p.timestamp.slice(0, 10) < day)
  return subtractMoney(latest.equity, (prior ?? curve[0]).equity)
}
