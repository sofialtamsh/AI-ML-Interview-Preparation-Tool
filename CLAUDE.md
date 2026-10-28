# Project guide

AI/ML interview-preparation platform (admin console + student app).

- **Requirements (source of truth):** `docs/MASTER_PROMPT.md`. Re-read the relevant section before
  starting a phase.
- **Decisions, data model, phase status, open inputs:** `docs/ARCHITECTURE.md`. Keep its phase table
  current.

## Non-negotiables to keep in mind

- Agents (exploration, market research) never trigger content generation or publishing. They
  produce intelligence and *pending* recommendations only, and an admin decides.
- Content starts with the pilot batch (2–3 domains × 2–3 subtopics). Generation beyond pilot topics
  stays blocked until an admin records explicit approval.
- Never fabricate interview questions, sources, company links or frequencies. Actual and generated
  questions stay distinguishable (`origin`), and provenance is preserved.
- Students never see company names, source URLs, agent output, unpublished content or other
  students' data. Enforce this in the backend (separate student-facing tables and schemas), not only
  in the UI.
- No placeholder screens or dead buttons. A nav entry only appears once its module works.
- Don't claim something works until it has been run and tested. Report blockers and needed inputs.

## Backend conventions (`backend/`)

- Every admin endpoint depends on `require_permission(...)` / `require_any_permission(...)` from
  `app/auth/deps.py`. Permissions live in `app/auth/permissions.py`. After adding one, run
  `uv run python -m app.cli sync-rbac`.
- Every student endpoint uses `get_student_context` and scopes queries to `ctx.student.id`. Never
  accept another student's id.
- Record privileged admin actions with `record_audit(...)`, and never put secrets in `details`.
- Every AI call goes through `OpenRouterClient` (`app/ai/openrouter.py`) with a `feature` name, so its
  cost lands in `ai_usage_events`. Never call a model provider directly.
- `audit_logs`, `login_events`, `ai_usage_events`, `raw_source_records` and `job_events` are
  append-only (a DB trigger rejects UPDATE and DELETE); `interview_sources` and `jobs` reject
  DELETE. Records are kept permanently, accounts are disabled and never deleted, and new log or
  source-record tables get the same trigger.
- Every request to an admin-configured URL goes through `SafeHttp` (`app/sources/http.py`), which
  provides SSRF blocking, origin-scoped credentials, size and time limits, retries and robots.txt.
  Never call httpx directly for source traffic. A new kind of source is a connector class in
  `CONNECTORS` with a strict settings model and `FieldSpec`s.
- Source secrets are stored only through the vault (`app/core/vault.py`, `IPP_CREDENTIALS_KEYS`)
  and are never returned, logged or audited. Audit entries name the fields, never the values.
- Long-running work is a job (`app/jobs/runner.py`) that only an explicit admin action creates.
  Handlers log through `JobContext` and raise `UserFacingError` for messages admins should see.
- Agent output is checked in code, not trusted:
  - structured output via `structured_chat` (strict schema, one repair attempt);
  - quotes and questions checked with `SourceText`;
  - names never inferred;
  - everything lands as pending review;
  - research claims need a retrieved source;
  - runs honour a spending limit.
- Content (`app/content/`): bodies are validated by `SCHEMAS` and stored in canonical form;
  versions are immutable (edit or restore = new version). Lifecycle steps go through
  `apply_transition` (`TRANSITIONS` holds the permissions). A Python lab publishes only after a
  passing code check of its exact program. Generation respects `may_generate` (the pilot gate).
  Students read content only via `app/api/student/learn.py` and `app/schemas/learn.py`, which strip
  `origin`/`source_ref`. After changing starter content or schemas, run
  `uv run python -m app.cli export-starter-fixture ../frontend/src/test/fixtures/starter-content.json`
  (a test fails otherwise) and `seed-pilot-content --refresh` on the dev database.
- Tests and browser checks never put invented intelligence into the dev database. Use the test
  DB, or a throwaway `ipp_e2e` database with a simulated OpenRouter (`tests/fake_ai.py`).
- Schema changes: edit models → `uv run alembic revision --autogenerate -m "..."` → review the file.
  `tests/test_platform.py` fails if models and migrations drift.
- Tests run against the `ipp_test` database (dropped and recreated per run). Run
  `uv run pytest`, `uv run ruff check .`, `uv run ruff format .`.

## Frontend conventions (`frontend/`)

- Call the API through `api()` in `src/lib/api.ts`, which adds the CSRF header and handles session
  expiry. Query keys live in `src/lib/queryClient.ts`.
- Admin nav entries live in `src/admin/nav.ts` with `anyOf` permissions. Routes in `src/router.tsx`
  are lazy-loaded and wrapped in `RequirePermission`.
- Charts follow the dataviz skill. Use design tokens from `src/index.css` (`brand-*`).
- Learning UI lives in `src/learn/`: `sections/` (one per content component, shared by the student
  topic page and the admin preview), `widgets/` (playgrounds; their maths is in `widgets/ml.ts` with
  unit tests), `Figures.tsx` (animated SVGs). The playground controls a widget offers must match
  `WIDGET_CONTROLS` in `backend/app/content/generation.py`. Python runs only through
  `src/lib/pyodide.ts` (Web Worker, time limit).
- Run `npm test`, `npm run typecheck`, `npm run build`.

## Local ports

Postgres 55432 (Docker, optional), API 8010, Vite 5173. Ports 5432/5433/8000 belong to other projects on the
dev machine.
