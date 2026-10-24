# sma-trend-timing — SMA trend timing (Faber)

Status: spec only. Implementation and backtest are tracked in separate tasks.
Proposal: #10 (approved by quant review). Strategy name in code: `sma-trend-timing`.

## Hypothesis

Assets trading above their long-term (about 10-month) moving average tend to keep
outperforming, and assets below it are where the deep drawdowns happen. Holding an asset
only while it is above that average, and sitting in cash otherwise, should cut maximum
drawdown and volatility substantially versus buy-and-hold while keeping a meaningful part
of the return. The claim is about **drawdown and risk-adjusted return**, not about beating
buy-and-hold on raw return in every regime.

## Source

- Faber, Mebane T. (2007), "A Quantitative Approach to Tactical Asset Allocation",
  *Journal of Wealth Management* 9(4), 69-79 (updated 2013 edition).
  https://papers.ssrn.com/sol3/papers.cfm?abstract_id=962461
  Reported: a 10-month SMA timing rule on US equities, foreign equities, bonds, REITs and
  commodities gave return similar to buy-and-hold with materially lower volatility and a
  much smaller maximum drawdown over the paper's sample.
- Background only: Moskowitz, Ooi and Pedersen (2012), "Time Series Momentum", *Journal of
  Financial Economics* 104(2). It tests a different rule (sign of 12-month return, futures,
  vol-scaled), so it supports trend persistence in general, not this exact rule.

These are published backtests: evidence, not a forecast of future returns.

## Signal timing (which variant is used)

**Default: Faber's month-end evaluation (`evaluation = "month_end"`).** The signal is
evaluated once a month, on the last trading day of the month, against the 10-month SMA of
month-end closes. This is the rule tested in Faber (2007).

**Comparison variant: daily check (`evaluation = "daily"`), 200-day SMA.** Evaluated on
every daily bar. This is **not** the rule tested in Faber (2007); it is a different variant
(closer to the common "200-day" rule of thumb). It flips more often in choppy markets, so
the paper's turnover and whipsaw figures do not carry over to it. It is run only as a
comparison to the month-end default.

If the daily variant passes only because of tuning, the month-end variant stays the default.

## Rules

All computations are causal and use only daily bars with timestamp <= t. Each instrument
is evaluated independently.

### Month-end variant (default)

- Bar t is a *month-end bar* if it is the last trading day of its calendar month (in
  US/Eastern exchange time; timestamps themselves stay UTC). The exchange calendar is known
  in advance, so knowing that t is the last trading day is not lookahead.
- At a month-end bar t, take the closes of the last `sma_months` month-end bars (including
  bar t). `SMA_t` is their mean.
- Signal: `close_t > SMA_t * (1 + band_pct)` -> target long;
  `close_t < SMA_t * (1 - band_pct)` -> target flat; otherwise keep the previous target.
  With the default `band_pct = 0` this is the plain rule: long if `close_t > SMA_t`, flat
  otherwise.
- No signal on non-month-end bars: the target is held.
- Warmup: no signal until `sma_months` month-end closes exist for the instrument.
- Band state: with `band_pct > 0`, the initial "previous target" is **flat**, so the first
  long signal after warmup is a buy and nothing is bought inside the band at start.
  (Irrelevant at the default `band_pct = 0`.)
- Month-end closes used in the SMA: the "close" of a month is the close of its last
  trading day. If that day's bar is missing or stale (see below), the SMA input for that
  month is the **last valid close of the month**, but no trade is made on that month.

### Daily variant (comparison)

- On every bar t, `SMA_t` is the mean of the last `sma_window` closes, including bar t.
- Same long/flat rule and band as above, evaluated every bar.
- Warmup: no signal until `sma_window` bars exist.

### Common to both

- Entry: target flips flat -> long on bar t: emit a buy `OrderIntent`. It fills at the
  **open of t+1** under the standard fill model (slippage + commission). Never at the
  close of t.
- Exit: target flips long -> flat on bar t: emit a sell `OrderIntent` for the whole
  position, filled at the open of t+1.
- Flat state is cash; no yield is assumed.

### Stale and missing bars

- A bar is **stale/missing** for instrument X at a scheduled trading day if no bar with
  that day's date (US/Eastern) exists for X, or its volume is 0, or its timestamp is not
  the expected session. The expected sessions come from the exchange calendar.
- On a stale/missing bar: skip the signal and keep the current position. A missed
  month-end signal is **not** made up on a later bar of the same month or the next month;
  the target is held until the next month-end.
- The SMA input for a month with a missing last-day bar is the last valid close of that
  month (no trade on it). If the whole month has no valid bar, that month is absent from
  the SMA window (the window is the last `sma_months` months that have a valid close).
- Unscheduled closures (the exchange is closed on a day the calendar lists as open, or
  the calendar helper is unavailable): treat the last day with bars in the month as not a
  month-end (no trade that month), because the calendar said another day was last. The
  report lists every month-end skipped for this reason or for stale/missing bars.
- Daily variant: a missing bar is skipped; the SMA uses the last `sma_window` valid
  closes.

### Execution details

- **Whole shares only**, rounded down. Cash left from rounding stays in cash.
- **Slipped price estimate** for sizing a buy on bar t (the open of t+1 is unknown):
  `est = close_t * (1 + slippage_bps/10000)`; quantity =
  `floor(target_value / est)` where `target_value` = 1/K of equity at close of t, less
  the commission. At fill time the actual fill is `open_{t+1} * (1 + slippage_bps/10000)`
  for buys and `open_{t+1} * (1 - slippage_bps/10000)` for sells.
- **Order of execution on one bar:** sells are filled before buys, so sale proceeds are
  available to the buys.
- **Cash shortfall:** if cash at fill time is insufficient for all pending buys (e.g.
  gap-up opens), every buy is cut **pro rata** by the same factor (then rounded down to
  whole shares) so the total never exceeds cash. No leverage.

### Sizing and gross exposure

- Equal weight over K instruments. An instrument is sized at 1/K of **current equity**
  when it (re-)enters; that amount stays in cash while the instrument is flat.
- No rebalancing between signal flips (winners are not trimmed, losers not topped up).
- **Gross exposure must stay <= 1.0x.** When several instruments re-enter on the same bar,
  each order is sized at 1/K of current equity using the slipped price estimate defined
  under "Execution details", and the total of long values plus pending buys must not
  exceed equity. If cash is insufficient at fill time, the pro-rata cut applies. No
  leverage, no shorting.

## Parameters and defaults

| Parameter | Default | Notes |
|---|---|---|
| `evaluation` | `"month_end"` | `"month_end"` (Faber, default) or `"daily"` (comparison variant) |
| `sma_months` | 10 | month-end variant; Faber's published value |
| `sma_window` | 200 | daily variant (trading days) |
| `band_pct` | 0.0 | hysteresis around the SMA. **Stays 0** unless counted as a tuned parameter |
| `universe` | SPY, QQQ, IWM, TLT, GLD | all in the docs/GOAL.md universe |

Bar size: daily.

### Tuning plan

- Month-end variant: the published 10 is used untuned.
- Daily variant: at most one parameter tuned (`sma_window`) on the coarse grid
  {100, 150, 200}, **in-sample only**. The published 200 remains the default.
- Total configurations tried: month-end 1 + daily 3 = **4**. The report must state the
  actual count, including any extra run. A non-zero `band_pct` would count as an added
  tuned parameter and add configurations.
- The out-of-sample period is run once per reported configuration and never used to choose.

## Costs, data and price adjustment (fixed for all runs)

- **Costs:** slippage 5 bps per fill and commission $1.00 per trade (fill), i.e. the
  `backend/app/config.py` defaults. The backtest task must set these explicitly (not rely
  on environment overrides, e.g. `SLIPPAGE_BPS`/`COMMISSION_PER_TRADE` must be unset or
  equal to these values) and the report records them. The strategy and **both benchmarks
  use the same costs** (the benchmark pays them on its single entry, per instrument).
- **Gross run:** a diagnostic run with zero slippage and zero commission, used only to
  compute cost drag (criterion 4). It is **not** counted as a configuration and is never
  used for selection.
- **Starting capital:** 100,000 (USD) for strategy and benchmarks.
- **Price adjustment:** Alpaca bars requested with `adjustment=all` (split and dividend
  adjusted). Signals (closes/SMA) and simulated fills (opens) both use these adjusted
  prices, and no separate dividend cash flow is modelled: dividends are implicitly
  reinvested while the instrument is held and not earned while flat. The benchmarks use
  the same adjusted prices, so dividends are treated identically. The same
  `adjustment` setting is used in live paper mode and in backtests. Caveat: adjusted
  history is restated after each distribution, so a backtest run later sees slightly
  different levels than a signal computed live on the day; the report records the fetch
  date.
- **Data feed:** Alpaca `feed=iex` (free plan), identical in live and backtest. Volumes
  are IEX-only and are not used except for the stale-bar check (volume 0).
- **Deviations from Faber (2007) that the report must list:** (1) universe of 5 liquid US
  ETFs (SPY, QQQ, IWM, TLT, GLD) rather than Faber's five asset-class indices; (2) the
  signal is computed at the month-end close but filled at the **next open** with slippage
  and commission, while Faber trades at the month-end close without costs; (3) IEX-feed
  ETF history from ~2016 instead of 1973 onward; (4) cash earns 0%, Faber credits T-bills;
  (5) dividends via adjusted prices, not total-return index series; (6) whole shares.

## Benchmarks

- **Primary:** equal-weight 1/K buy-and-hold. At the start of the evaluated period buy 1/K
  of starting capital in each instrument at the open of the first bar (whole shares,
  slippage and commission as above), hold to the end, **no rebalancing**.
- **Secondary:** per-instrument buy-and-hold for each of the K instruments, same costs.

## Backtest protocol and pass criteria (from the quant review on #10)

Evaluated on the equal-weight 5-ETF portfolio, after slippage and commission.

- **Data limitation:** Alpaca free-plan (IEX) history starts around 2016. After warmup
  (10 months for month-end, 200 bars for daily) the usable sample is roughly 2017 onward,
  with essentially two bear episodes (2020, 2022). **2000-02 and 2008 cannot be tested**,
  so the "works best" regimes cited from Faber are not verifiable with our data. The report
  must say so.
- **OOS split:** the last ~30% of the usable (post-warmup) history is held out. The split
  date is fixed in the backtest task **before any results are seen** and recorded in the
  report, together with a **fixed end date** for the data. The split falls on a **month
  boundary** (OOS starts on the first trading day of a month). Both variants use the same
  split, end date and evaluation window.
- **Fresh start at the OOS date:** the OOS run is a new run that warms up the SMA on
  pre-OOS bars **without trading**, starts **flat with 100,000 cash** on the OOS start
  date, and takes the first long signal as a buy (no inherited positions from the
  in-sample run). The benchmark starts on the same date with the same capital. All OOS
  metrics are computed on the OOS equity curve rebased to the start.
- **Regime coverage warning:** with ~30% held out, OOS starts around late 2023, so both
  bear markets (2020, 2022) fall in-sample and the OOS period may contain no bear market
  at all. The report must (a) list the drawdown episodes (peak, trough, depth,
  duration) of the equal-weight buy-and-hold for the in-sample and the OOS period
  separately, and (b) state the number of OOS month-end decisions (about 36 expected).
  If OOS contains no buy-and-hold drawdown deeper than ~10%, criterion 1 is reported but
  flagged as uninformative rather than passed on its own.
- **Risk-free rate and annualization:** Sharpe uses rf = 0% (consistent with cash earning
  nothing) and an annualization factor of sqrt(252) on daily returns. The report states both.

**Which configuration is judged:** the pass criteria 1-3 apply **only** to the
pre-registered default: `evaluation="month_end"`, `sma_months=10`, `band_pct=0`. The
daily variant is **informational**: it is reported but cannot be promoted, selected or
enabled on the basis of OOS results, and a daily-variant pass does not rescue a
month-end failure.

The strategy is kept only if, **out-of-sample** (month-end default config):

1. Max drawdown <= 2/3 of equal-weight buy-and-hold's max drawdown over the same period.
2. Sharpe >= buy-and-hold Sharpe - 0.1.
3. Annualized volatility is below buy-and-hold.
4. Cost drag is reported (gross vs net return) along with round trips per instrument per
   year. If net return < 50% of gross, or the average exceeds ~12 round trips per
   instrument per year, the default needs revisiting.
5. Both the month-end and daily variants are reported (daily informational only), with
   the total number of configurations tried (the gross diagnostic run excluded). Month-end
   remains the default regardless of how the daily variant does.

If criterion 1 or 2 fails OOS, the strategy is **not** enabled in live paper mode. A
rejected strategy is a valid outcome. Results are evidence, not predictions; backtest
returns must never be described as expected real returns.

## Expected regime

Sustained trends and large bear markets, where the rule moves to cash before most of the
decline. Faber's sample includes 2000-02 and 2008; of the bear episodes only 2020 and 2022
fall inside our data (plus the 2018 Q4 drawdown), and all of these are likely in-sample.

## Known failure modes

- **Whipsaw** in range-bound markets: repeated false crosses, each paying slippage and
  commission. Much worse for the daily variant (clusters in e.g. 2015-16, 2018, 2022).
- **Late re-entry** after sharp V-shaped recoveries (e.g. March 2020). The month-end
  variant can lag by up to a month on top of the SMA lag itself.
- **Lag:** exits only after a decline of roughly 5-15%.
- **Correlated signals:** SPY, QQQ and IWM often flip together, so real diversification
  comes mainly from TLT and GLD.
- **Idle cash earns nothing** in the default setup, which understates the rule when rates
  are high.
- **Short, regime-limited sample** (see data limitation); low statistical power.
- **Data gaps** on the IEX feed: signals are skipped on missing bars and positions are
  kept rather than trading on bad data.

## Engine needs

- Multi-symbol `StrategyContext` (tracked in #20). Fallback: one instance per instrument
  with 1/K of capital, which cannot enforce the cross-instrument gross-exposure check on
  its own and then relies on the engine's no-leverage risk limit.
- `ctx` must provide enough daily history per instrument (about 200 bars; the month-end
  variant needs about 10 months of closes), plus positions and cash, and a way to know
  whether bar t is the last trading day of its month without peeking at future bars
  (e.g. an exchange-calendar helper).
- Data adapter must request `adjustment=all` and `feed=iex` (see above) and expose stale
  or missing bars so the strategy can detect them.
- Standard buy-and-hold benchmark comparison in M3 reports (equal-weight and
  per-instrument, as defined above).
