# Paper Trading Platform - top-level developer commands.
# See CLAUDE.md's "Commands" table for the contract these targets must honor.
#
# Works with GNU Make on Linux/macOS/CI, and on Windows under a shell that
# provides `make` (e.g. Git Bash + make, MSYS2, or WSL). Picks the right
# virtualenv layout (bin/ vs Scripts/) based on $(OS), which Windows sets to
# "Windows_NT" in its process environment.

PYTHON ?= python3
BACKEND_DIR := backend
FRONTEND_DIR := frontend
STRATEGY ?=

ifeq ($(OS),Windows_NT)
	VENV_BIN := Scripts
	VENV_PY_NAME := python.exe
else
	VENV_BIN := bin
	VENV_PY_NAME := python
endif

VENV_PY := .venv/$(VENV_BIN)/$(VENV_PY_NAME)

.PHONY: setup setup-backend setup-frontend \
        test test-backend test-frontend \
        lint lint-backend lint-frontend \
        dev backtest paper

setup: setup-backend setup-frontend

setup-backend:
	$(PYTHON) -m venv $(BACKEND_DIR)/.venv
	cd $(BACKEND_DIR) && $(VENV_PY) -m pip install --upgrade pip
	cd $(BACKEND_DIR) && $(VENV_PY) -m pip install -e ".[dev]"

setup-frontend:
	cd $(FRONTEND_DIR) && npm install
	cd $(FRONTEND_DIR) && npx playwright install --with-deps chromium

test: test-backend test-frontend

test-backend:
	cd $(BACKEND_DIR) && $(VENV_PY) -m pytest

test-frontend:
	cd $(FRONTEND_DIR) && npm run test
	cd $(FRONTEND_DIR) && npm run test:e2e

lint: lint-backend lint-frontend

lint-backend:
	cd $(BACKEND_DIR) && $(VENV_PY) -m ruff check .
	cd $(BACKEND_DIR) && $(VENV_PY) -m mypy

lint-frontend:
	cd $(FRONTEND_DIR) && npm run lint
	cd $(FRONTEND_DIR) && npm run typecheck

# Runs the backend API and the frontend dev server together. Ctrl+C stops
# the foreground (frontend) process; the backgrounded uvicorn process may
# need a manual `kill` afterwards depending on your shell.
dev:
	@echo "Starting backend (uvicorn, :8000) and frontend (vite, :5173)..."
	cd $(BACKEND_DIR) && $(VENV_PY) -m uvicorn app.main:app --reload --port 8000 & \
	cd $(FRONTEND_DIR) && npm run dev

# Thin stub: the backtesting engine lands in milestone M3. Exits 0 so
# scripts calling `make backtest` don't fail while the real thing is built.
backtest:
	@echo "make backtest: the backtest engine is not implemented yet (milestone M3)."
	@echo "Requested strategy: $(STRATEGY)"
	@exit 0

# Thin stub: the live paper-trading loop lands in milestone M5.
paper:
	@echo "make paper: the live paper-trading loop is not implemented yet (milestone M5)."
	@exit 0
