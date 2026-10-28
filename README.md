# AI/ML Interview Preparation & Intelligence Platform

An EdTech platform that makes students interview-ready for AI/ML engineering roles, with two
securely separated experiences: a **student** learning app and an **admin** console.

- Product requirements: [docs/MASTER_PROMPT.md](docs/MASTER_PROMPT.md)
- Architecture, data model, decisions and open inputs: [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)

**Status:** Phases 1–4 (foundation, interview data sources, intelligence agents, learning
content for the pilot topics) and AI spend tracking are complete. See "What works today" below.

## Stack

FastAPI · SQLAlchemy 2 · Alembic · PostgreSQL 17 · React 19 · TypeScript · Vite · TanStack Query ·
Tailwind CSS 4. Background jobs use a Postgres-backed queue, so there is no Redis dependency.

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
uv run python -m app.cli generate-credentials-key   # paste into IPP_CREDENTIALS_KEYS in .env
uv run alembic upgrade head
uv run python -m app.cli sync-rbac
uv run python -m app.cli seed-taxonomy   # the starting AI/ML domains and topics (once)
uv run python -m app.cli seed-pilot-content   # pilot topics + starter drafts to review (once)
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
- Interview-source credentials are encrypted with `IPP_CREDENTIALS_KEYS`. Keep that key safe;
  rotate it with `uv run python -m app.cli rotate-credentials` (see `app/cli.py`).
- Background jobs (source fetches, agents, generation, narration) run inside the API process. To run them separately, set
  `IPP_EMBEDDED_WORKER=false` and start `uv run python -m app.cli run-worker`.

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

## What works today (Phases 1–4)

**Students**
- Register and sign in.
- Reset a forgotten password by email link (single-use, 30 minutes).
- Edit profile and change password.
- See signed-in devices and sign them out.
- Personal dashboard with the published topics.
- **Explore and learn** (six pilot topics: Supervised Learning, Unsupervised Learning, Regression,
  Neural Network Fundamentals, Activation Functions, Optimizers). Each topic has:
  - **Learn:** swipeable bite-size cards with animated figures, myth vs fact, formulas, key terms;
  - **Play:** an interactive playground (k-NN, k-means, line fitting, a trainable neural network,
    activation functions, gradient descent / Momentum / Adam) with "try this" tasks;
  - **Watch:** a narrated explainer, scene by scene, with captions;
  - **Code:** real Python (NumPy, scikit-learn) that runs and can be edited in the browser;
  - **Interview:** questions by level with strong answers, what the interviewer wants, follow-ups;
  - **Quiz:** instant feedback and a score (not saved yet; that is Phase 6);
  - **Revise:** a five-minute cheat sheet.

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

**Interview sources** (admin, `sources.*` permissions)
- Add, edit, turn off and remove sources:
  - website pages;
  - JSON APIs;
  - RSS/Atom feeds;
  - file imports.

  A new URL is configuration, not code.
- Credentials are encrypted and write-only. Six sign-in methods are supported, including a website
  login form.
- Test a connection, and fetch one or several sources in the background. A run shows live progress,
  a log, and a Stop button.
- Runs are incremental: unchanged items are skipped, and changed ones are stored as new revisions.
- Import CSV, JSON, PDF, Word, text, Markdown or saved HTML files into any source.
- Browse the raw records (`intelligence.view`).
- Safety:
  - private and internal addresses are blocked;
  - robots.txt is honoured;
  - CAPTCHAs and two-factor prompts are reported, never bypassed;
  - credentials are only ever sent to the source's own site.

**Agents & intelligence** (`agents.*`, `intelligence.*`, `taxonomy.manage`)
- **Exploration agent:** it reads unread source records and extracts interviews and questions.
  It flags anything not word-for-word in the record, drops company names the record doesn't
  contain, and stops at a per-run spending limit.
- **Interview intelligence:**
  - a review queue grouped by interview: approve, reject, re-topic, merge repeats, correct details;
  - approved questions with how many records they appear in;
  - a topic view that sets interview evidence beside the market trend.
- **Market research:** cited web research by role and region. Uncited findings are dropped and
  quotes are checked. Recommendations wait for a decision, and approving "add a topic" adds it
  to the taxonomy. It produces research-derived practice questions (kept separate from real
  ones), and nothing is generated.
- **Agent runs:** every fetch, import and agent run, with log, cost, Stop and Run again.
- Models are settings: `IPP_MODEL_EXTRACTION`, `IPP_MODEL_RESEARCH`, `IPP_RESEARCH_SEARCH_ENGINE`.

**Content** (`content.generate`, `content.review`, `content.publish`, `taxonomy.manage`)
- **Content studio:** every pilot topic × component with its review status and what is live.
  - Generate drafts for chosen topics and components, optionally grounded in approved
    intelligence, with a spending limit. One run per topic, with log and cost.
  - Review: preview exactly what students see, edit (saved as a new version and validated),
    compare versions, restore, submit, approve, publish, unpublish, reject, archive, or do it in
    bulk per topic. Every step is audited.
  - A Python lab can't be published until its exact code has passed a check run in the browser.
  - Narrate a video with an Indian-English voice.
  - **Pilot gate:** generation only works for pilot topics until an admin with the settings
    permission approves expansion.
- **Domains & topics:** add, rename, archive and restore domains and topics; choose pilot topics.
- The starter drafts for the six pilot topics were written by the development assistant and are
  labelled as such. They go through the same review as AI drafts.

**AI layer**
- Every model call goes through `app/ai/openrouter.py` and is recorded with its cost in
  `ai_usage_events`, a permanent, append-only ledger.

**Permanent records**
- The database rejects any change to or deletion of the audit log, sign-in history, AI spend
  ledger, raw source records, job logs and code checks. Sources, runs, content items, content
  versions and media can't be deleted either, and a version's content can't be changed.

**Security**
- Separate admin and student identities and sessions, with path-scoped httpOnly cookies.
- Argon2id password hashing.
- Lockout after repeated failures, plus per-IP rate limits.
- CSRF header check and security headers.
- Backend-enforced permission checks on every admin endpoint.

Navigation only lists modules that work. Each later phase adds its own section.

## Deployment notes (expanded in Phase 7)

- Run `alembic upgrade head` and then `python -m app.cli sync-rbac` on every deploy (and
  `seed-taxonomy` and `seed-pilot-content` once on a new database).
- Students' browsers load Pyodide from `cdn.jsdelivr.net` for the Code section; a strict
  Content-Security-Policy must allow it.
- Set `IPP_ENVIRONMENT=production` and `IPP_COOKIE_SECURE=true` (the app refuses to start without
  them). Serve the built SPA (`frontend/dist`) and the API from the **same origin** behind a reverse
  proxy that terminates TLS.
- Configure secrets through the environment or a secrets manager. Never commit `.env` files.
- The per-IP auth rate limiter is in-process. When running several API instances, rely on the
  DB-backed account lockout or move the counters to a shared store.
