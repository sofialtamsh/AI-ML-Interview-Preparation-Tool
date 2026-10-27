# AI/ML Interview Preparation & Intelligence Platform

An EdTech platform that makes students interview-ready for AI/ML engineering roles, with two
securely separated experiences: a **student** learning app and an **admin** console.

- Product requirements: [docs/MASTER_PROMPT.md](docs/MASTER_PROMPT.md)
- Architecture, data model, decisions and open inputs: [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)

**Status:** Phase 1 (foundation) and AI spend tracking are complete. See "What works today" below.

## Stack

FastAPI · SQLAlchemy 2 · Alembic · PostgreSQL 17 · React 19 · TypeScript · Vite · TanStack Query ·
Tailwind CSS 4. Background jobs (Phase 3) will use a Postgres-backed queue, so there is no Redis
dependency.

## Prerequisites

Python ≥ 3.12 with [uv](https://docs.astral.sh/uv/), Node ≥ 20, and a PostgreSQL 17 database.
Docker is optional. It is only the quickest way to get that database locally (see "Without Docker"
below). The app itself never needs Docker, in development or in production.

| Service | Port |
|---|---|
| PostgreSQL (Docker, optional) | 55432 |
| API (uvicorn) | 8010 |
| Web (Vite) | 5173 (proxies `/api` → 8010) |

## Run locally

```bash
# 1. Database (creates `ipp` and the throwaway `ipp_test`)
docker compose up -d --wait postgres

# 2. API
cd backend
cp .env.example .env
uv sync
uv run alembic upgrade head
uv run python -m app.cli sync-rbac
uv run python -m app.cli create-admin --email you@yourcompany.com --name "Your Name"   # prompts for a password
uv run uvicorn app.main:app --port 8010 --reload

# 3. Web (new terminal)
cd frontend
npm install
npm run dev
```

- Student app: http://localhost:5173. Register an account there.
- Admin console: http://localhost:5173/admin/login
- API docs (non-production only): http://localhost:8010/api/docs
- Password-reset emails are printed to the API console until an email provider is configured.
- AI features use OpenRouter. Put the key in `backend/.env` as `IPP_OPENROUTER_API_KEY=...` and
  restart the API. Settings → AI usage then shows the key as connected.

### Without Docker

Any PostgreSQL 17 works: a native Windows/macOS install or a free cloud database such as Neon.
1. Create two databases, `ipp` and `ipp_test`, owned by a user that can create tables.
2. Set `IPP_DATABASE_URL` in `backend/.env` to the `ipp` database. Before running tests, set
   `IPP_TEST_DATABASE_URL` in the environment to the `ipp_test` database. The tests refuse any
   database whose name doesn't end in `_test`, because they wipe it.
3. Continue from step 2 above. Nothing else changes.

## Tests

```bash
cd backend && uv run pytest          # wipes and re-migrates the ipp_test database
cd backend && uv run ruff check . && uv run ruff format --check .
cd frontend && npm test && npm run typecheck && npm run build
```

The backend suite includes an authorization sweep. It calls **every** admin endpoint, discovered
from the OpenAPI schema, with a student session and with no session, and expects 401. New admin
endpoints are covered automatically.

## What works today (Phase 1)

**Students**
- Register and sign in.
- Reset a forgotten password by email link (single-use, 30 minutes).
- Edit profile and change password.
- See signed-in devices and sign them out.
- Personal dashboard.

**Admins**
- Sign in, with a forced change of any temporary password.
- Overview with real registration and activity metrics.
- Student directory: search, filter, pagination, detail with sign-in history, suspend/deactivate,
  cohorts.
- Admin accounts and roles: six system roles plus custom roles, with self-lock-out and
  last-Super-Admin guards.
- Audit log.
- **AI usage** (Settings, Super Admin by default):
  - weekly AI spend in USD since 27 Oct 2026, in Tuesday–Monday India-time weeks;
  - a breakdown of each week by feature and by model;
  - the live OpenRouter key status: lifetime spend, spending cap, and remaining credit.

**AI layer**
- Every model call goes through `app/ai/openrouter.py` and is recorded with its cost in
  `ai_usage_events`, a permanent, append-only ledger.

**Permanent records**
- The database rejects any change to or deletion of the audit log, sign-in history and AI spend
  ledger.

**Security**
- Separate admin and student identities and sessions, with path-scoped httpOnly cookies.
- Argon2id password hashing.
- Lockout after repeated failures, plus per-IP rate limits.
- CSRF header check and security headers.
- Backend-enforced permission checks on every admin endpoint.

Navigation only lists modules that work. Each later phase adds its own section.

## Deployment notes (expanded in Phase 7)

- Run `alembic upgrade head` and then `python -m app.cli sync-rbac` on every deploy.
- Set `IPP_ENVIRONMENT=production` and `IPP_COOKIE_SECURE=true` (the app refuses to start without
  them). Serve the built SPA (`frontend/dist`) and the API from the **same origin** behind a reverse
  proxy that terminates TLS.
- Configure secrets through the environment or a secrets manager. Never commit `.env` files.
- The per-IP auth rate limiter is in-process. When running several API instances, rely on the
  DB-backed account lockout or move the counters to a shared store.
