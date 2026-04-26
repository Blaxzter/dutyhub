# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Package Managers

- **Backend:** `uv` only — never pip/pip3
- **Frontend:** `pnpm` only — never npm/yarn

## Common Commands

Use `just <command>` (see `justfile`) for most tasks.

### Development

Two modes, controlled by `dev_mode` at the top of `justfile` (default: `"local"`):

```bash
just dev               # Uses dev_mode default
just dev docker        # Full stack via Docker Compose watch (hot reload)
just dev local         # Starts DB+Adminer in Docker; run backend/frontend manually:
just dev-backend       #   terminal 1
just dev-frontend      #   terminal 2
```

`just test-e2e` also respects `dev_mode`: docker runs Playwright in a container, local runs `pnpm test:e2e` directly.

Local URLs: frontend `http://localhost:5555`, backend `http://localhost:8787`, OpenAPI docs `http://localhost:8787/docs`

### Linting & Formatting

```bash
just lint                     # Both backend + frontend
just lint-backend             # ruff + basedpyright
just lint-frontend            # ESLint
just format                   # Both
```

### Testing

```bash
just test-backend             # pytest with coverage (runs inside backend/)
bash ./backend/scripts/test.sh
pnpm --prefix frontend test:e2e   # Playwright E2E
```

Run a single backend test:
```bash
cd backend && uv run pytest tests/api/test_users.py::test_read_user -v
```

### Database Migrations

```bash
# Inside backend/ venv or container:
alembic revision --autogenerate -m "Add <feature>"
alembic upgrade head

# Or via just:
just migration "Add <feature>"
just migrate
```

### API Client Generation

Run after any backend OpenAPI schema change:
```bash
just generate-client          # or: cd frontend && pnpm run generate-client
```

## Architecture Overview

### Stack

- **Backend:** FastAPI + SQLModel (async SQLAlchemy) + PostgreSQL + Auth0 (JWT via `auth0-fastapi-api`)
- **Frontend:** Vue 3 + TypeScript + Vite + Pinia + Vue Router + Tailwind CSS v4 + shadcn-vue
- **Infra:** Docker Compose + Traefik reverse proxy + GitHub Actions

### Backend Pattern (Model → Schema → CRUD → Route → Register)

```
backend/app/
├── models/        # SQLModel table definitions
├── schemas/       # Pydantic create/read/update schemas
├── crud/          # CRUDBase + per-model classes
├── api/routes/    # FastAPI routers (one file per domain)
├── api/api.py     # Router registration
├── logic/         # Business logic / services
└── core/          # config.py, db.py, auth.py, errors.py
```

When adding a feature: model → schema → CRUD → route → register in `api/api.py` → Alembic migration.

### Auth Pattern

From `backend/app/api/deps.py`:

- `CurrentUser` — validates JWT, checks DB user exists and is active; use for all protected endpoints
- `CurrentSuperuser` — admin-only (e.g., delete/create users)
- `CurrentUser` + `claims: dict = Depends(auth0.require_auth())` — when you need both DB user and Auth0 profile data (e.g., `/me` endpoints)
- `auth0.require_auth()` alone — only for Auth0-specific operations with no DB requirement

On first login the frontend calls `POST /users/me` with Auth0 profile data; backend upserts the user and seeds demo data.

### Frontend Structure

```
frontend/src/
├── client/        # AUTO-GENERATED from OpenAPI — never hand-edit
├── stores/        # Pinia (auth.ts, breadcrumb.ts, dialog.ts)
├── router/        # Vue Router (PreAuth / PostAuth layouts + authGuard)
├── views/         # Page components (preauth/ and authenticated)
├── components/ui/ # shadcn-vue components — add via CLI only
├── locales/{en,de}/ # i18n JSON — both locales required
└── composables/   # Vue composables
```

Two layouts: `PreAuthLayout` (public pages) and `PostAuthLayout` (authenticated pages, wraps with `authGuard`).

### Frontend–Backend Connection

- API base path: `/api/v1`
- Frontend reads `VITE_API_URL` (set to `http://localhost:8787/api/v1` locally)
- Auto-generated client in `src/client/` handles auth tokens and typed requests

## Shell Commands

- **Never use `cd <dir> && <command>`** — this triggers an extra permission prompt. Instead use `--prefix`, `--cwd`, or run the command with an absolute/relative path directly (e.g., `pnpm --prefix frontend generate-changelog`, `uv run --directory backend pytest`).

## Key Rules

- **Tailwind CSS v4:** Config is CSS-only in `src/index.css` — do not create `tailwind.config.js`
- **shadcn-vue:** Add components via `npx shadcn-vue@latest add <component>` from `frontend/` — do not manually create files in `src/components/ui/`
- **i18n:** All user-facing strings must have keys in both `src/locales/en/` and `src/locales/de/`
- **Generated client:** Never edit `frontend/src/client/` — regenerate with `just generate-client` instead
- **API path:** `API_V1_STR = "/api/v1"` in `backend/app/core/config.py`
- **basedpyright:** Run `uv run basedpyright` (no arguments) inside `backend/` — never pass `.` as it bypasses the `include` config and crawls `.venv`

## Environment

- Root `.env` — used by Docker Compose (copy from `.env.example`); restart stack after changes
- `frontend/.env` — Vite env vars (copy from `frontend/.env.example`)
- Auth0 is required for any auth flow; set `AUTH0_DOMAIN`, `AUTH0_AUDIENCE`, `AUTH0_CLIENT_ID`, `AUTH0_CLIENT_SECRET` in root `.env` and their `VITE_*` equivalents in `frontend/.env`
- E2E tests require `E2E_AUTH0_USERNAME` and `E2E_AUTH0_PASSWORD` in `frontend/.env`

## Template Cleanup (when starting a new project)

```bash
just remove-examples     # Remove demo views and example routes
just remove-domain       # Remove sample Projects/Tasks domain
just clean-template      # Both + regenerate client
```
