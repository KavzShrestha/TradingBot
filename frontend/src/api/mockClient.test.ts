import { describe, expect, it } from 'vitest'
import { createApiClient } from './index'
import { createMockClient } from './mockClient'

describe('mock API client', () => {
  const client = createMockClient()

  it('returns 2-3 strategies deterministically', async () => {
    const a = await client.listStrategies()
    const b = await createMockClient().listStrategies()
    expect(a.length).toBeGreaterThanOrEqual(2)
    expect(a.length).toBeLessThanOrEqual(3)
    expect(a).toEqual(b)
  })

  it('uses string money values and ISO UTC timestamps', async () => {
    const curve = await client.getEquityCurve('sma_crossover')
    for (const p of curve) {
      expect(typeof p.equity).toBe('string')
      expect(p.timestamp).toMatch(/^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$/)
    }
    const trades = await client.listTrades()
    expect(trades.every((t) => typeof t.price === 'string')).toBe(true)
  })

  it('equity curve ends at the strategy summary equity', async () => {
    for (const s of await client.listStrategies()) {
      const curve = await client.getEquityCurve(s.name)
      expect(curve[curve.length - 1].equity).toBe(s.equity)
    }
  })

  it('filters by strategy and rejects unknown ones', async () => {
    const trades = await client.listTrades('rsi_mean_reversion')
    expect(trades.length).toBeGreaterThan(0)
    expect(trades.every((t) => t.strategy === 'rsi_mean_reversion')).toBe(true)
    await expect(client.getStrategy('nope')).rejects.toThrow('Unknown strategy')
  })

  it('returns metrics and backtests with in/out-of-sample periods', async () => {
    const m = await client.getMetrics('sma_crossover')
    expect(m.benchmark.symbol).toBe('SPY')
    const bts = await client.listBacktests('sma_crossover')
    expect(bts).toHaveLength(1)
    expect(bts[0].out_of_sample.start > bts[0].in_sample.end).toBe(true)
  })

  it('does not let callers mutate fixtures', async () => {
    const first = await client.listStrategies()
    first[0].name = 'mutated'
    expect((await client.listStrategies())[0].name).toBe('sma_crossover')
  })

  it('factory defaults to the mock client', async () => {
    expect((await createApiClient().listStrategies()).length).toBeGreaterThan(0)
  })
})
