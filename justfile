set shell := ["bash", "-cu"]
set windows-shell := ["C:/Program Files/Git/bin/bash.exe", "-cu"]

# Default: list available recipes
default:
    @just --list

# ── Development ───────────────────────────────────────────────

# Start all services with Docker Compose watch mode
dev:
    docker compose watch

# Start backend dev server directly (no Docker)
dev-backend:
    cd backend && uv run fastapi dev app/main.py

# Start frontend dev server directly (no Docker)
dev-frontend:
    cd frontend && pnpm dev

# ── Linting & Formatting ─────────────────────────────────────

# Lint backend (ruff + basedpyright)
lint-backend:
    cd backend && uv run ruff check app && uv run ruff format app --check && uv run basedpyright app

# Format backend (ruff)
format-backend:
    cd backend && uv run ruff check app scripts --fix && uv run ruff format app scripts

# Lint frontend (eslint)
lint-frontend:
    cd frontend && pnpm lint

# Format frontend (prettier)
format-frontend:
    cd frontend && pnpm format

# Lint everything
lint: lint-backend lint-frontend

# Format everything
format: format-backend format-frontend

# ── Testing ───────────────────────────────────────────────────

# Run backend tests with coverage
test-backend:
    cd backend && uv run coverage run --source=app -m pytest && uv run coverage report --show-missing

# Run frontend type check
type-check:
    cd frontend && pnpm type-check

# Run Playwright e2e tests in Docker
test-e2e:
    docker compose run --rm playwright npx playwright test

# ── Database ──────────────────────────────────────────────────

# Run Alembic migrations
migrate:
    cd backend && uv run alembic upgrade head

# Create a new Alembic migration (usage: just migration "add users table")
migration message:
    cd backend && uv run alembic revision --autogenerate -m "{{message}}"

# Seed the database with demo data
seed:
    cd backend && uv run python -m app.scripts.initial_data

# ── Code Generation ──────────────────────────────────────────

# Regenerate the frontend API client from backend OpenAPI spec
generate-client:
    cd backend && uv run python -c "import app.main; import json; print(json.dumps(app.main.app.openapi()))" > ../frontend/openapi.json
    cd frontend && pnpm generate-client
    cd frontend && pnpm exec prettier --write ./src/client
    rm -f frontend/openapi.json

# ── Upstream Sync ─────────────────────────────────────────────

# Add the upstream template remote (run once after forking)
add-upstream url:
    python scripts/sync_upstream.py --add-remote {{url}}

# Fetch and merge upstream template changes into your fork
sync-upstream remote="upstream" branch="main":
    python scripts/sync_upstream.py --remote {{remote}} --branch {{branch}}

# ── Build & Deploy ────────────────────────────────────────────

# Build frontend for production
build-frontend:
    cd frontend && pnpm build

# Build Docker images
build tag="latest":
    TAG={{tag}} FRONTEND_ENV=production docker compose -f docker-compose.yml build

# ── Pre-commit ────────────────────────────────────────────────

# Run all pre-commit hooks
pre-commit:
    cd backend && uv run pre-commit run --all-files
