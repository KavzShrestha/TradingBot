# CLAUDE.md — Paper Trading Platform

This file is the rulebook for every agent working in this repo. Read it fully, then read
`docs/GOAL.md`, `docs/PLAN.md` and your task issue before starting any task.

## Mission

Build an automated **paper-trading** platform:

1. Strategies (from published/theoretical ideas) generate trade signals.
2. Signals are executed against **live market data** using **simulated fills and fake money**.
3. The same strategies can be **backtested** on historical data with identical logic.
4. A **web dashboard** shows live positions, P&L, equity curves and per-strategy analytics.

The trading bot itself is ordinary, deterministic software. Agents build and improve it;
agents never make trading decisions at runtime.

---

## Hard rules (never break these)

1. **Paper money only.** Never call a real order-placement endpoint. The broker/exchange
   client must only point at paper/sandbox URLs or at the internal simulator. The app must
   refuse to start unless `PAPER_TRADING=true`, and must refuse any base URL on the
   live-endpoint denylist in `backend/app/config.py`.
2. **Never commit secrets.** Use `.env` (gitignored) and keep `.env.example` up to date
   with dummy values. API keys must be read-only / market-data-only where possible.
3. **Never push to `main` and never merge PRs.** Work on a branch and open a PR. Only the
   human owner merges.
4. **Never weaken checks to get green CI.** Do not delete, skip, or loosen tests, lint
   rules, or type checks. If a test is wrong, fix it and explain why in the PR.
5. **One task per PR.** Each PR closes exactly one task issue (`Closes #<n>`) and uses its
   task ID. Aim for under ~400 changed lines; split larger work.
6. **Protected files.** Do not modify `CLAUDE.md`, `.claude/`, `docs/GOAL.md`, or
   `.github/workflows/` unless the task explicitly says so.
7. **When unsure, ask, don't guess.** For ambiguous or architectural decisions, open a
   draft PR or an issue labelled `question` describing the options and your recommendation.

---

## Architecture

```
backend/                  Python 3.12, FastAPI
  app/
    config.py             settings, env loading, live-endpoint denylist
    data/                 market data adapters -> normalized Bar/Tick models
    strategies/           one module per strategy, implements Strategy protocol
    engine/               event loop: data -> strategy -> OrderIntent -> simulated fill
    portfolio/            ledger, positions, cash, P&L, risk limits, metrics.py
    backtest/             historical replay using the SAME engine
    api/                  REST + WebSocket endpoints for the frontend
    storage/              DB models and migrations (SQLite in dev, Postgres later)
  tests/
frontend/                 React + TypeScript + Vite
  src/
    pages/                Overview, Strategy detail, Positions, Trades, Backtests
    components/           charts, tables, metric cards
    api/                  typed client for backend REST/WebSocket
docs/
  GOAL.md                 the end goal (human-owned)
  PLAN.md                 milestones (planner-owned); tasks live in GitHub Issues
  strategies/             one write-up per strategy
  adr/                    architecture decision records
.github/workflows/        CI (human-owned)
```

### Core design principle

**Backtest and live paper trading share the same Strategy, Engine and Portfolio code.**
Only the data source and the clock differ. Never write a separate "backtest version" of a
strategy.

### Strategy interface

```python
class Strategy(Protocol):
    name: str
    params: dict

    def on_bar(self, bar: Bar, ctx: StrategyContext) -> list[OrderIntent]: ...
```

Strategies are pure: no network calls, no DB access, no reading the wall clock, no global
state. Everything they need (history, current positions, cash) comes through `ctx`.

---

## Simulation rules

- **No lookahead.** A strategy may only see data with timestamp <= the current bar.
  Indicators must be computed causally.
- **Realistic fills.** A signal generated on bar `t` fills at the open of bar `t+1` (or
  the next tick in live mode), plus configurable slippage (bps) and commission. Never fill
  at the close of the bar that produced the signal.
- **Time.** All timestamps are timezone-aware UTC.
- **Money.** Use `Decimal` for cash, prices in the ledger, and P&L. Floats are fine inside
  indicator math only.
- **Ledger.** Every fill is appended to an immutable `trades` table. Positions and equity
  are derived from the ledger, never stored as the only source of truth.
- **Risk limits** (configurable per strategy): max position size as % of equity, max gross
  exposure (default 1.0x, no leverage), daily loss limit that halts the strategy, global
  kill switch.
- **Market hours / gaps.** Handle market closures, missing bars and reconnects without
  generating trades from stale data.

## Metrics

All metrics live in `backend/app/portfolio/metrics.py` (single source of truth; the
frontend never recomputes them). Required: equity curve, total return, annualized return,
annualized volatility, Sharpe and Sortino (state risk-free rate and annualization factor),
max drawdown and duration, win rate, profit factor, average win/loss, exposure, turnover,
and comparison to a buy-and-hold benchmark of the same instrument.

---

## Commands

The first milestone creates a `Makefile`. Always use these targets:

| Command | Purpose |
|---|---|
| `make setup` | install backend + frontend dependencies |
| `make test` | all backend and frontend tests |
| `make lint` | ruff + mypy (backend), eslint + tsc (frontend) |
| `make dev` | run backend and frontend locally |
| `make backtest STRATEGY=<name>` | run a backtest and write a report to `reports/` |
| `make paper` | start the live paper-trading loop |

Quality bars:

- Backend: `ruff`, `mypy --strict` on `app/`, `pytest`. Coverage >= 80% for `engine/`
  and `portfolio/`.
- Frontend: `eslint`, `tsc --noEmit`, `vitest`, plus a Playwright smoke test that loads
  each page.

---

## Definition of done (every PR)

- [ ] Closes its task issue (`Closes #<n>`); the PR has labels `agent` and `role:<role>`.
- [ ] Tests added or updated; `make test` and `make lint` pass locally.
- [ ] PR description includes: **What / Why / How tested / Risks**, and screenshots for
      any UI change.
- [ ] Docs updated if behavior, config, or commands changed.
- [ ] No secrets, no new heavy dependency without a one-line justification.

## Conventions

- Branch names: `<role>/<task-id>-<short-desc>`, e.g. `backend/M2-03-fill-model`.
- Conventional commits: `feat:`, `fix:`, `test:`, `docs:`, `refactor:`, `chore:`.
- Keep functions small and typed. Prefer clarity over cleverness.
- Don't refactor code unrelated to your task.

## Strategy research rules

Every new strategy needs `docs/strategies/<name>.md` containing: hypothesis, exact entry
and exit rules, parameters and their defaults, source (paper/book/article), the market
regime it should work in, and known failure modes.

Before a strategy is enabled in live paper mode it must have a backtest report with:
in-sample and out-of-sample periods, results after costs, comparison to buy-and-hold, and
a note on how many parameters were tuned. Treat results as evidence, not predictions;
never describe backtest returns as expected real returns.

---

## Agent roles

Defined in `.claude/agents/`. Each agent stays inside its role.

| Agent | Owns | May edit |
|---|---|---|
| `planner` | turning milestones, approved proposals and flagged work into task issues | task issues, `docs/PLAN.md`, `docs/adr/` |
| `strategy-researcher` | strategy ideas (proposal issues), specs, implementations, backtests | `backend/app/strategies/`, `docs/strategies/`, related tests |
| `backend-engineer` | data, engine, portfolio, API, storage | `backend/` (not `strategies/` logic) |
| `frontend-engineer` | dashboards and UI | `frontend/` |
| `quant-reviewer` | approving strategy proposals; correctness of trading logic | nothing (review only) |
| `code-reviewer` | general code quality and safety | nothing (review only) |

## Task board and how agents collaborate

Agents run in parallel as separate GitHub Actions jobs and coordinate only through
GitHub Issues, labels and PRs. Nobody edits another agent's in-progress work.

```
strategy-researcher --proposal issue--> quant-reviewer --proposal-approved--> planner
planner --task issues (role:*)--> backend / frontend / strategy workers --PR--> reviewers --> human merges
anyone --needs-planning issue--> planner
```

| Label | Meaning |
|---|---|
| `task` | a unit of work = one PR. Title starts with its ID, e.g. `M2-04: fill model` |
| `role:backend` / `role:frontend` / `role:strategy` | which worker picks it up (also put on that worker's PR) |
| `milestone:M#` | milestone from `docs/PLAN.md` |
| `status:todo` → `status:in-progress` → `status:in-review` → closed by the merged PR | task lifecycle |
| `status:blocked` | waiting on something other than an issue; reason in the body |
| `proposal` | a strategy idea from the researcher, waiting for the quant-reviewer |
| `proposal-approved` / `proposal-rejected` | quant-reviewer's verdict |
| `planned` | an approved proposal the planner has turned into tasks |
| `needs-planning` | extra work someone found; the planner turns it into tasks |

- Dependencies: the last line of a task body is `Depends on: #12, #15`. A task is ready
  when it is `status:todo` and every issue it depends on is closed.
- Found work outside your task? Don't do it. Open an issue labelled `needs-planning`.
- Each role has at most one open agent PR at a time.
