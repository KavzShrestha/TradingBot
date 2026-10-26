/**
 * Display-only helpers for decimal-string money values (see api/types.ts).
 * Sums use BigInt cents so no float error creeps in; these are aggregations of
 * backend-provided figures, not metric calculations.
 */

const MONEY_RE = /^(-?)(\d+)(?:\.(\d{1,2}))?$/

export function toCents(value: string): bigint {
  const m = MONEY_RE.exec(value)
  if (!m) throw new Error('Invalid money value: ' + value)
  const cents = BigInt(m[2]) * 100n + BigInt((m[3] ?? '').padEnd(2, '0') || '0')
  return m[1] === '-' ? -cents : cents
}

export function fromCents(cents: bigint): string {
  const negative = cents < 0n
  const abs = negative ? -cents : cents
  const whole = abs / 100n
  const frac = (abs % 100n).toString().padStart(2, '0')
  return `${negative ? '-' : ''}${whole}.${frac}`
}

export function sumMoney(values: string[]): string {
  return fromCents(values.reduce((acc, v) => acc + toCents(v), 0n))
}

export function subtractMoney(a: string, b: string): string {
  return fromCents(toCents(a) - toCents(b))
}

/** "$10,450.00", or "+$450.00" / "−$200.00" when `signed`. */
export function formatMoney(value: string, signed = false): string {
  const cents = toCents(value)
  const abs = cents < 0n ? -cents : cents
  const whole = (abs / 100n).toString().replace(/\B(?=(\d{3})+(?!\d))/g, ',')
  const body = `$${whole}.${(abs % 100n).toString().padStart(2, '0')}`
  if (cents < 0n) return '−' + body
  return signed && cents > 0n ? '+' + body : body
}

/** Fraction -> signed percent string, e.g. 0.045 -> "+4.50%". */
export function formatPercent(fraction: number, signed = true): string {
  const pct = Math.abs(fraction * 100).toFixed(2)
  if (fraction < 0 && Number(pct) !== 0) return '−' + pct + '%'
  return (signed && fraction > 0 && Number(pct) !== 0 ? '+' : '') + pct + '%'
}
