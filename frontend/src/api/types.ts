/**
 * API contract between the dashboard and the backend.
 *
 * The backend API task MUST return JSON matching these shapes exactly.
 *  - Money values (cash, prices, P&L, equity, commission) are decimal STRINGS,
 *    e.g. "10234.50", never JSON numbers. The frontend never does arithmetic on them.
 *  - Timestamps are ISO-8601 strings in UTC with a trailing "Z".
 *  - Ratios/fractions (returns, drawdown, win rate, exposure) are plain numbers,
 *    where 0.05 means 5%. Drawdown is reported as a non-positive fraction.
 *  - Every metric is computed by backend/app/portfolio/metrics.py. The frontend only
 *    displays these values and must never recompute them.
 *  - Nullable metrics (null) mean "not enough data to compute".
 */

/** Decimal-safe money value, e.g. "1234.56". */
export type Money = string
/** ISO-8601 UTC timestamp, e.g. "2025-01-02T14:30:00Z". */
export type IsoTimestamp = string

export type StrategyStatus = 'running' | 'halted' | 'stopped'
export type Side = 'buy' | 'sell'

export interface StrategySummary {
  name: string
  description: string
  status: StrategyStatus
  params: Record<string, number | string | boolean>
  equity: Money
  total_pnl: Money
  total_return: number
  open_positions: number
}

export interface EquityPoint {
  timestamp: IsoTimestamp
  equity: Money
}

export interface Position {
  strategy: string
  symbol: string
  quantity: string
  avg_price: Money
  market_price: Money
  market_value: Money
  unrealized_pnl: Money
}

export interface Trade {
  id: string
  strategy: string
  symbol: string
  side: Side
  quantity: string
  price: Money
  commission: Money
  slippage_bps: number
  timestamp: IsoTimestamp
}

export interface BenchmarkComparison {
  symbol: string
  total_return: number
  annualized_return: number | null
  max_drawdown: number
  /** Strategy total return minus buy-and-hold total return. */
  excess_return: number
}

export interface Metrics {
  total_return: number
  annualized_return: number | null
  annualized_volatility: number | null
  sharpe: number | null
  sortino: number | null
  /** Annual risk-free rate assumed for Sharpe/Sortino (fraction). */
  risk_free_rate: number
  /** Periods per year used to annualize (e.g. 252 for daily US equities). */
  annualization_factor: number
  /** Non-positive fraction, e.g. -0.12 for a 12% drawdown. */
  max_drawdown: number
  max_drawdown_duration_days: number
  win_rate: number | null
  profit_factor: number | null
  avg_win: Money | null
  avg_loss: Money | null
  /** Fraction of time with capital deployed. */
  exposure: number
  turnover: number
  benchmark: BenchmarkComparison
}

export interface BacktestPeriod {
  start: IsoTimestamp
  end: IsoTimestamp
}

export interface BacktestSummary {
  id: string
  strategy: string
  symbol: string
  created_at: IsoTimestamp
  in_sample: BacktestPeriod
  out_of_sample: BacktestPeriod
  initial_cash: Money
  final_equity: Money
  commission_bps: number
  slippage_bps: number
  parameters_tuned: number
  /** Metrics after costs. */
  in_sample_metrics: Metrics
  out_of_sample_metrics: Metrics
}

export interface ApiClient {
  listStrategies(): Promise<StrategySummary[]>
  getStrategy(name: string): Promise<StrategySummary>
  getEquityCurve(strategy: string): Promise<EquityPoint[]>
  getMetrics(strategy: string): Promise<Metrics>
  listPositions(strategy?: string): Promise<Position[]>
  listTrades(strategy?: string): Promise<Trade[]>
  listBacktests(strategy?: string): Promise<BacktestSummary[]>
}
