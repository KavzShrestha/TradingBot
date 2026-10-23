# PLAN (planner-owned)

Status values: `todo`, `in progress`, `in review`, `done`, `blocked: <reason>`.
Each task = one PR. The planner expands each milestone into tasks when it starts.

## M0 — Skeleton and guardrails
| ID | Title | Role | Status |
|---|---|---|---|
| M0-01 | Repo scaffold: backend (FastAPI), frontend (Vite React TS), Makefile with all targets, pre-commit, .env.example | backend-engineer | done |
| M0-02 | Config with `PAPER_TRADING` guard and live-endpoint denylist + tests that the app refuses to start otherwise | backend-engineer | in review |
| M0-03 | CI passes on an empty app (lint, type check, tests, Playwright smoke) | backend-engineer | todo |

## M1 — Data
Market data adapter(s) to normalized `Bar` model, historical download + local cache,
live streaming with reconnect and gap detection.

## M2 — Engine, simulator and portfolio
Strategy protocol, event loop, next-bar fill model with slippage/commission, immutable
trade ledger, positions/cash derived from ledger, risk limits and kill switch, metrics.py.

## M3 — Backtesting
Historical replay through the same engine, report generation (JSON + HTML) with
in-sample/out-of-sample split and buy-and-hold benchmark. Reference strategy:
SMA crossover.

## M4 — Strategies
3+ strategies from documented sources, each with spec, tests and backtest report.

## M5 — Live paper trading
`make paper` runs the engine on live data, persists state, recovers after restart,
publishes updates over WebSocket.

## M6 — Dashboard
Overview (total equity, P&L today, per-strategy cards), strategy detail (equity curve,
drawdown, metrics table, trades), positions, trades history, backtest reports viewer.

## M7 — Hardening
Week-long unattended run, alerting on errors/halts, docs, deployment to a small server.
