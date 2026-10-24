import type {
  ApiClient,
  BacktestSummary,
  EquityPoint,
  Metrics,
  Position,
  StrategySummary,
  Trade,
} from './types'

/** Deterministic fixture data; no randomness or wall-clock reads. */

const STRATEGIES: StrategySummary[] = [
  {
    name: 'sma_crossover',
    description: 'Long when fast SMA is above slow SMA.',
    status: 'running',
    params: { fast: 20, slow: 50 },
    equity: '10450.00',
    total_pnl: '450.00',
    total_return: 0.045,
    open_positions: 1,
  },
  {
    name: 'rsi_mean_reversion',
    description: 'Buy oversold RSI, exit on reversion.',
    status: 'halted',
    params: { period: 14, oversold: 30 },
    equity: '9800.00',
    total_pnl: '-200.00',
    total_return: -0.02,
    open_positions: 0,
  },
  {
    name: 'donchian_breakout',
    description: 'Long on N-day high breakout.',
    status: 'stopped',
    params: { lookback: 55 },
    equity: '10000.00',
    total_pnl: '0.00',
    total_return: 0,
    open_positions: 0,
  },
]

const SYMBOL: Record<string, string> = {
  sma_crossover: 'SPY',
  rsi_mean_reversion: 'QQQ',
  donchian_breakout: 'SPY',
}

const FINAL_EQUITY: Record<string, number> = {
  sma_crossover: 10450,
  rsi_mean_reversion: 9800,
  donchian_breakout: 10000,
}

const START_MS = Date.UTC(2025, 0, 2, 21, 0, 0)
const DAY_MS = 86_400_000
const POINTS = 30

function curve(strategy: string): EquityPoint[] {
  const final = FINAL_EQUITY[strategy] ?? 10000
  const points: EquityPoint[] = []
  for (let i = 0; i < POINTS; i++) {
    // Deterministic wiggle that vanishes on the last point so it ends at `final`.
    const progress = i / (POINTS - 1)
    const wiggle = Math.sin(i * 1.3) * 40 * (1 - progress)
    const value = 10000 + (final - 10000) * progress + wiggle
    points.push({
      timestamp: new Date(START_MS + i * DAY_MS).toISOString().replace('.000Z', 'Z'),
      equity: value.toFixed(2),
    })
  }
  return points
}

// Fixture values only: the real backend computes these in portfolio/metrics.py.
function metricsFor(strategy: string, scale: number): Metrics {
  const ret = ((FINAL_EQUITY[strategy] ?? 10000) - 10000) / 10000
  return {
    total_return: ret * scale,
    annualized_return: ret * scale * 4,
    annualized_volatility: 0.11,
    sharpe: ret >= 0 ? 0.9 * scale : -0.4,
    sortino: ret >= 0 ? 1.2 * scale : -0.5,
    risk_free_rate: 0.02,
    annualization_factor: 252,
    max_drawdown: -0.06,
    max_drawdown_duration_days: 12,
    win_rate: 0.55,
    profit_factor: ret >= 0 ? 1.4 : 0.8,
    avg_win: '85.00',
    avg_loss: '-60.00',
    exposure: 0.62,
    turnover: 3.1,
    benchmark: {
      symbol: SYMBOL[strategy] ?? 'SPY',
      total_return: 0.03,
      annualized_return: 0.12,
      max_drawdown: -0.08,
      excess_return: ret * scale - 0.03,
    },
  }
}

const POSITIONS: Position[] = [
  {
    strategy: 'sma_crossover',
    symbol: 'SPY',
    quantity: '10',
    avg_price: '500.00',
    market_price: '505.50',
    market_value: '5055.00',
    unrealized_pnl: '55.00',
  },
]

const TRADES: Trade[] = [
  {
    id: 't-1',
    strategy: 'sma_crossover',
    symbol: 'SPY',
    side: 'buy',
    quantity: '10',
    price: '500.00',
    commission: '1.00',
    slippage_bps: 1,
    timestamp: '2025-01-10T14:30:00Z',
  },
  {
    id: 't-2',
    strategy: 'rsi_mean_reversion',
    symbol: 'QQQ',
    side: 'buy',
    quantity: '5',
    price: '420.00',
    commission: '1.00',
    slippage_bps: 1,
    timestamp: '2025-01-12T14:30:00Z',
  },
  {
    id: 't-3',
    strategy: 'rsi_mean_reversion',
    symbol: 'QQQ',
    side: 'sell',
    quantity: '5',
    price: '410.00',
    commission: '1.00',
    slippage_bps: 1,
    timestamp: '2025-01-20T14:30:00Z',
  },
]

function backtestFor(strategy: string): BacktestSummary {
  return {
    id: 'bt-' + strategy,
    strategy,
    symbol: SYMBOL[strategy] ?? 'SPY',
    created_at: '2025-02-01T00:00:00Z',
    in_sample: { start: '2020-01-01T00:00:00Z', end: '2022-12-31T00:00:00Z' },
    out_of_sample: { start: '2023-01-01T00:00:00Z', end: '2024-12-31T00:00:00Z' },
    initial_cash: '10000.00',
    final_equity: (FINAL_EQUITY[strategy] ?? 10000).toFixed(2),
    commission_bps: 1,
    slippage_bps: 2,
    parameters_tuned: 2,
    in_sample_metrics: metricsFor(strategy, 1),
    out_of_sample_metrics: metricsFor(strategy, 0.5),
  }
}

function byStrategy<T extends { strategy: string }>(items: T[], strategy?: string): T[] {
  return strategy === undefined ? items : items.filter((i) => i.strategy === strategy)
}

function requireStrategy(name: string): StrategySummary {
  const found = STRATEGIES.find((s) => s.name === name)
  if (!found) throw new Error('Unknown strategy: ' + name)
  return found
}

export function createMockClient(): ApiClient {
  // Deep-copy so callers cannot mutate the shared fixtures.
  const clone = <T>(v: T): T => structuredClone(v)
  return {
    listStrategies: () => Promise.resolve(clone(STRATEGIES)),
    getStrategy: async (name) => clone(requireStrategy(name)),
    getEquityCurve: async (strategy) => curve(requireStrategy(strategy).name),
    getMetrics: async (strategy) => metricsFor(requireStrategy(strategy).name, 1),
    listPositions: (strategy) => Promise.resolve(clone(byStrategy(POSITIONS, strategy))),
    listTrades: (strategy) => Promise.resolve(clone(byStrategy(TRADES, strategy))),
    listBacktests: (strategy) =>
      Promise.resolve(byStrategy(STRATEGIES.map((s) => backtestFor(s.name)), strategy)),
  }
}
