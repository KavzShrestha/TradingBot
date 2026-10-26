import { describe, expect, it } from 'vitest'

import { formatMoney, formatPercent, sumMoney } from './money'
import { combineEquityCurves, pnlToday } from './portfolio'

describe('money', () => {
  it('sums without float error', () => {
    expect(sumMoney(['0.10', '0.20', '-0.05'])).toBe('0.25')
  })
  it('formats with separators and signs', () => {
    expect(formatMoney('1234567.5')).toBe('$1,234,567.50')
    expect(formatMoney('450.00', true)).toBe('+$450.00')
    expect(formatMoney('-200.00', true)).toBe('−$200.00')
    expect(formatMoney('0.00', true)).toBe('$0.00')
  })
  it('formats percents', () => {
    expect(formatPercent(0.045)).toBe('+4.50%')
    expect(formatPercent(-0.02)).toBe('−2.00%')
    expect(formatPercent(0)).toBe('0.00%')
  })
})

describe('portfolio', () => {
  const a = [
    { timestamp: '2025-01-01T21:00:00Z', equity: '100.00' },
    { timestamp: '2025-01-02T21:00:00Z', equity: '110.00' },
  ]
  const b = [{ timestamp: '2025-01-02T21:00:00Z', equity: '50.00' }]

  it('combines curves, excluding strategies before their first point', () => {
    expect(combineEquityCurves([a, b]).map((p) => p.equity)).toEqual(['100.00', '160.00'])
  })
  it('computes P&L since the previous UTC day', () => {
    expect(pnlToday(combineEquityCurves([a, b]))).toBe('60.00')
    expect(pnlToday(a)).toBe('10.00')
    expect(pnlToday([])).toBe('0.00')
  })
})
