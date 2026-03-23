# Kainex — Multi-market Quantitative Trading Platform

# Default recipe
default:
  @just --list

# ─── Development ───────────────────────────────────────────────

# Start all services for development
dev:
  just web &
  just collector &
  just engine &
  wait

# Start frontend only
web:
  pnpm --filter @kainex/web dev

# Start collector service
collector:
  cd services/collector && uv run python -m collector.main

# Start engine API server
engine:
  cd services/engine && uv run uvicorn engine.api.main:app --reload --host 0.0.0.0 --port 8000

# ─── Build ─────────────────────────────────────────────────────

# Build frontend
build:
  pnpm --filter @kainex/web build

# Type check frontend
typecheck:
  pnpm --filter @kainex/web typecheck

# Lint frontend
lint:
  pnpm --filter @kainex/web lint

# ─── Python ────────────────────────────────────────────────────

# Install Python dependencies for all services
py-install:
  cd services/collector && uv sync
  cd services/engine && uv sync

# Run Python tests
py-test:
  cd services/collector && uv run pytest
  cd services/engine && uv run pytest

# Seed sample data for development
seed:
  cd services/collector && uv run python scripts/seed_data.py

# ─── Setup ─────────────────────────────────────────────────────

# First-time project setup
setup:
  pnpm install
  just py-install
  @echo "Kainex is ready. Run 'just dev' to start."
