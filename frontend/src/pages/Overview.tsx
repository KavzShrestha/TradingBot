import { useEffect, useState } from 'react'

import { createApiClient } from '../api'
import type { ApiClient, EquityPoint, StrategySummary } from '../api'
import { EquityCurveChart } from '../components/charts/EquityCurveChart'
import { MetricCard } from '../components/MetricCard'
import { PaperBanner } from '../components/PaperBanner'
import { formatMoney, formatPercent } from '../lib/money'
import { combineEquityCurves, pnlToday } from '../lib/portfolio'

interface StrategyView {
  summary: StrategySummary
  maxDrawdown: number
}

type State =
  | { kind: 'loading' }
  | { kind: 'error'; message: string }
  | { kind: 'ready'; strategies: StrategyView[]; combined: EquityPoint[] }

async function load(client: ApiClient): Promise<State> {
  const summaries = await client.listStrategies()
  const details = await Promise.all(
    summaries.map(async (summary) => {
      const [curve, metrics] = await Promise.all([
        client.getEquityCurve(summary.name),
        client.getMetrics(summary.name),
      ])
      return { view: { summary, maxDrawdown: metrics.max_drawdown }, curve }
    }),
  )
  return {
    kind: 'ready',
    strategies: details.map((d) => d.view),
    combined: combineEquityCurves(details.map((d) => d.curve)),
  }
}

/** Overview page: total equity, P&L today, per-strategy cards, combined equity curve. */
export function Overview({ client }: { client?: ApiClient }) {
  const [state, setState] = useState<State>({ kind: 'loading' })

  useEffect(() => {
    let cancelled = false
    void (async () => {
      try {
        const next = await load(client ?? createApiClient())
        if (!cancelled) setState(next)
      } catch (err) {
        if (!cancelled) {
          setState({ kind: 'error', message: err instanceof Error ? err.message : String(err) })
        }
      }
    })()
    return () => {
      cancelled = true
    }
  }, [client])

  return (
    <main>
      <PaperBanner />
      <h1>Overview</h1>
      <OverviewBody state={state} />
    </main>
  )
}

function OverviewBody({ state }: { state: State }) {
  if (state.kind === 'loading') return <p role="status">Loading…</p>
  if (state.kind === 'error') return <p role="alert">Failed to load overview: {state.message}</p>
  if (state.strategies.length === 0) return <p>No strategies yet.</p>

  const latest = state.combined[state.combined.length - 1]
  return (
    <>
      <div className="metric-card-row">
        <MetricCard label="Total equity" value={latest ? formatMoney(latest.equity) : '—'} />
        <MetricCard label="P&L today" value={formatMoney(pnlToday(state.combined), true)} />
      </div>
      <h2>Combined equity</h2>
      <EquityCurveChart points={state.combined} title="Combined equity curve" />
      <h2>Strategies</h2>
      {state.strategies.map(({ summary, maxDrawdown }) => (
        <section key={summary.name} className="strategy-card" aria-label={summary.name}>
          <h3>{summary.name}</h3>
          <div className="metric-card-row">
            <MetricCard label="Equity" value={formatMoney(summary.equity)} />
            <MetricCard label="Return" value={formatPercent(summary.total_return)} />
            <MetricCard label="Max drawdown" value={formatPercent(maxDrawdown)} />
          </div>
        </section>
      ))}
    </>
  )
}
