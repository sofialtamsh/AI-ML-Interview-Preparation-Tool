# Architecture & Delivery Plan

Requirements: [MASTER_PROMPT.md](MASTER_PROMPT.md). This document records the decisions made to
satisfy them. It is kept short on purpose; details live in code, migrations and tests.

## 1. Starting point

The repository was empty on 2026-10-26 (greenfield). Local toolchain: Node 24, Python 3.14, uv,
Docker. Another project on the same machine already uses ports 5432/5433/8000/6379, so this project uses
**55432** (Postgres) and **8010** (API).

## 2. Technology stack

| Layer | Choice | Why |
|---|---|---|
| API | **Python + FastAPI**, Pydantic v2 | The AI side of the product (agents, LLM SDKs, document parsing, testing generated NumPy/scikit-learn code) is Python. One language for the API, workers and agents avoids a second runtime. FastAPI gives typed validation and OpenAPI for free. |
| ORM / migrations | **SQLAlchemy 2.0 (sync) + Alembic**, psycopg 3 | Mature, explicit SQL control, reviewable migrations. Sync sessions in FastAPI's threadpool are simpler and well proven. Request handlers are short DB calls; slow LLM work never runs in a request. |
| Database | **PostgreSQL 17** | Relational integrity for provenance, versions and attempts. JSONB holds structured content bodies. Full-text search covers question search. `pgvector` is added only when semantic duplicate detection needs it (Phase 3). |
| Background jobs | **Postgres-backed job queue** (`jobs` table, `FOR UPDATE SKIP LOCKED`) + separate worker process | Agent and generation jobs are low-volume and long-running, and they need durable status, progress, history and retry, which means a table anyway. This avoids running Redis/Celery for no extra value. Swap in a broker only if throughput ever requires it. |
| Frontend | **React + TypeScript + Vite**, React Router, TanStack Query, Tailwind CSS v4 | A SPA fits a cookie-authenticated API on the same origin. TanStack Query handles caching and deduplication, which avoids redundant API calls. Tailwind provides a consistent design system with small CSS output. Admin and student code are lazily loaded, separate chunks. |
| Visualizations | Hand-built SVG/Canvas React components (D3 helpers where useful) | Interactive, parameter-driven playgrounds such as gradient descent, K-Means and attention. Static images are not acceptable. |
| Code playground | **Pyodide (CPython in WebAssembly) in a Web Worker** in the student's browser | Student code never runs on our servers, which satisfies the isolation requirement at zero server cost. Generated reference code is verified server-side in a network-less, resource-limited container (Phase 4/5). |
| AI layer | **OpenRouter** through one client (`app/ai/openrouter.py`) + per-task model routing + usage ledger | One key reaches many vendors' models, so each task can use a different model (cheap ones for classification, stronger ones for generation and evaluation). Models are configuration, not code. Every call records its USD cost in `ai_usage_events` (implemented 2026-10-27). |
| Video | Script → scene plan → visuals → TTS → assembly, behind provider interfaces | Narration uses OpenRouter's text-to-speech endpoint (`POST /audio/speech`) with the same key and the same cost ledger. |
| Media storage | Storage interface: local filesystem in dev, S3-compatible bucket in prod | No extra infrastructure until media exists. |

## 3. System overview

```
Browser SPA ──/admin/*──► cookie ipp_admin_session  (Path=/api/admin)  ──► FastAPI /api/admin/*  ─┐
            ──/app/*────► cookie ipp_student_session (Path=/api/student) ──► FastAPI /api/student/* ─┤
                                                                                                    ├─► PostgreSQL
Worker process (polls jobs table) ── agents, content generation, quality checks, analytics ─────────┘
        └──► LLM providers · interview sources (connectors) · web search · TTS · object storage
```

Backend modules (one package each, added phase by phase): `auth` (sessions, RBAC), `admin`,
`students`, `sources` (connectors + encrypted credentials), `agents` (exploration, research),
`intelligence`, `taxonomy`, `content` (generation, versions, review, quality), `learning`
(student read models), `assessments`, `progress`/`analytics`, `performance_intel` (role readiness),
`jobs`, `llm`.

Agents and the Studio never call each other. They communicate only through the database (jobs,
intelligence records, recommendations), so every hand-off is visible and reviewable.

## 4. Database design

Conventions: UUID primary keys (big-integer identity for high-volume append-only logs), timezone-aware
timestamps, enums stored as constrained strings (easy to migrate), soft deletion where provenance must
survive, and append-only history tables (attempts, events, versions) that are never overwritten.

**Identity & access (Phase 1, implemented)**
- `admin_users`, `roles`, `permissions`, `role_permissions`, `admin_user_roles`
- `students` (UUID `id` + human-readable `student_number` → `STU-001001`), `cohorts`
- `auth_sessions`: one table with an `audience` column ∈ {admin, student} and a CHECK constraint that
  exactly the matching principal FK is set.
- `password_reset_tokens`, `login_events`, `audit_logs`

**AI spend (implemented 2026-10-27)**
- `ai_usage_events`: one row per billed AI call (provider, feature, model, generation id, tokens,
  `cost_usd`, triggering admin). It is written in its own transaction, so spend is kept even if
  the job fails. Weekly reports are aggregated from it, so they never need separate snapshots.

**Permanent records:** activity logs and source records are kept permanently (product owner
decision, 2026-10-27). A database trigger rejects any UPDATE or DELETE on `audit_logs`,
`login_events` and `ai_usage_events`. Phase 2–3 tables (`raw_source_records`, extraction and
research records) get the same treatment. Accounts are disabled, never deleted, so log references
stay valid.

**Sources & agents (Phases 2–3)**
- `interview_sources`: name, base URL, connector type, auth method, non-secret config (JSONB),
  enabled flag, connection status, last attempted/successful sync, incremental sync cursor.
- `source_credentials`: Fernet ciphertext + key version, plus the *names* of the stored fields only.
  Secrets are never returned by any API.
- `jobs` (kind, status, payload, progress, attempts, heartbeat, error, result, triggered_by,
  parent batch) and `job_events` (execution log).
- `raw_source_records` (source, external id, URL, content hash, fetched at). Unique on
  (source, external id), which makes exploration incremental and auditable.
- `interview_experiences` → `interview_questions` (actual questions): company, role, round,
  date or period, original text, technologies, difficulty, topic, extraction confidence,
  verification status, `duplicate_of`, provenance FKs to source, raw record and job.
- `question_clusters`: groups near-duplicate questions. Frequency is always *computed* as the count
  of distinct verified records and is never stored as a free-form claim.
- `research_reports` → `research_findings` → `research_sources` (URL, publisher, access date).
- `curriculum_recommendations` (pending / approved / rejected / deferred, decided by and at).
  Recommendations stay separate from curriculum decisions.

**Taxonomy & content (Phases 4–5)**
- `domains`, `topics` (self-referencing `parent_id` → topic/subtopic), `job_roles`,
  `topic_role_relevance`, with an `is_pilot` flag on topics.
- `content_items` (one per topic × component: concept, examples, python, interview Q&A, revision,
  assessment, visualization spec, video script, video) pointing at `published_version_id`.
- `content_versions` (immutable body JSONB, version number, lifecycle status
  draft → under_review → approved → published → archived/rejected, generated_by, model, job,
  reviewer, notes, quality report).
- `content_intelligence_links`: content version ↔ interview questions / research findings it used.
- `practice_questions`: what students see. `origin` ∈ {actual_interview, ai_generated,
  research_derived, admin_created}, with a CHECK that `actual_interview` ⇔ FK to an
  `interview_questions` row. **This table has no company column.** Student APIs only ever read
  this table, so company names are structurally unreachable from student endpoints.
- `quality_checks`, `generation_batches`, `media_assets`, `platform_settings`. `ai_usage_events`
  gains job/topic/batch links when jobs exist.

**Learning & performance (Phase 6)**
- `learning_events` (append-only: topic viewed, section completed, video progress, exercise done,
  revision viewed, interview question attempted, …)
- `topic_progress` (current state per student × topic; completion is separate from mastery)
- `assessments` → `assessment_questions`; `assessment_attempts` (never overwritten) →
  `attempt_responses`
- `interview_practice_attempts`, `student_topic_mastery`, `student_performance_snapshots` (trends)
- `role_evaluation_frameworks` (versioned, transparent factor weights and minimum-evidence
  thresholds), `student_role_evaluations` (measured metrics kept separate from the AI narrative,
  readiness band including `insufficient_data`), `evaluation_overrides` (admin challenge/override
  with reason).

## 5. Authentication

Two independent identity spaces, so a student credential can never become an admin credential.

| | Admin | Student |
|---|---|---|
| Accounts | Created by an admin with `admins.manage`; first super admin via CLI | Self-registration |
| Login | `POST /api/admin/auth/login` | `POST /api/student/auth/login` |
| Cookie | `ipp_admin_session`, `Path=/api/admin` | `ipp_student_session`, `Path=/api/student` |
| Lifetime | 12 h absolute, 2 h idle | 30 days |
| Password reset | By another admin; `must_change_password` on next login | Emailed single-use token (30 min) |

Shared mechanics:
- **Sessions:** opaque 256-bit random tokens. Only their SHA-256 hash is stored, so DB leaks don't
  leak sessions. Cookies are httpOnly, Secure and SameSite=Lax. Server-side revocation supports
  logout, logging out other devices, and immediate cut-off when an account is suspended or disabled.
  Multiple concurrent sessions are allowed (multi-device).
- **Cookie path scoping:** the browser never sends a student cookie to admin APIs or vice versa,
  and the server additionally checks the session's audience.
- **Passwords:** Argon2id (argon2-cffi), rehashed on login when parameters change. Unknown-email
  logins verify against a dummy hash so response timing doesn't reveal which accounts exist.
- **Brute force:** per-IP rate limits on auth endpoints, plus a DB-backed lockout after 5
  consecutive failures for 15 minutes. A password reset clears the lockout.
- **CSRF:** SameSite cookies + a mandatory `X-Requested-With` header on every API call. CORS is
  closed by default, so cross-site pages cannot send it.
- **Records:** `login_events` records every attempt, and `audit_logs` records every privileged
  admin action.

## 6. Authorization

Admin permissions are fine-grained keys defined in code (`app/auth/permissions.py`) and synced to the
DB. Roles are sets of permissions. Every admin endpoint declares its permission, and the backend
enforces it. The UI filters navigation using the same keys, but only for convenience.

| Permission | Meaning |
|---|---|
| `admins.manage`, `roles.manage`, `audit.view`, `settings.manage` | Platform administration |
| `ai_usage.view` | Weekly AI spend in USD and the OpenRouter key's cap (Super Admin only by default) |
| `sources.view`, `sources.manage`, `sources.credentials.manage` | Interview data sources & secrets |
| `agents.view`, `agents.run` | See / trigger agent runs |
| `intelligence.view`, `intelligence.review` | Raw interview records incl. company names / approve extractions |
| `taxonomy.manage` | Domains, topics, approving curriculum recommendations |
| `content.generate`, `content.review`, `content.publish` | Studio / review / publish (separable) |
| `students.view`, `students.manage` | Student directory / account status & cohorts |
| `analytics.view`, `analytics.export`, `rankings.view` | Analytics, exports, role-readiness rankings |

System roles (read-only and re-synced from code): **Super Admin** (everything), **Intelligence
Operator**, **Content Manager**, **Content Reviewer & Publisher**, **Student Success**, **Analyst**.
Admins can create custom roles. Safeguards: an admin cannot disable themselves or remove their own
admin-management access, and the last active Super Admin cannot be removed.

Students have no permissions. Every student endpoint is scoped to `current_student.id` inside the
query itself, so there is no endpoint that takes another student's ID.

## 7. AI agents

**Interview Exploration Agent.** It runs only on an explicit admin trigger
(`agents.run`); nothing in a login or page view can enqueue it.
1. The admin selects one or more enabled sources, which creates one job per source.
2. The worker claims the job, loads the connector by type, and decrypts credentials in memory only.
3. `test_connection()`, then incremental listing from the stored cursor. Unchanged
   records (same content hash) are skipped.
4. Raw records are stored. LLM extraction produces structured output validated against a Pydantic
   schema (invalid output is retried, then recorded as a partial failure).
5. Normalisation and taxonomy classification run on a cheap model. Duplicate detection runs exact
   hash first, then semantic similarity.
6. The output is an **extraction report**. Records land as `pending_review`, and an admin with
   `intelligence.review` approves, rejects or merges them. Only approved records count in the
   intelligence engine.

Connectors use a plugin interface (`test_connection`, `list_records(cursor)`, `fetch(record)`).
Generic connectors (REST/JSON API, configurable web pages, RSS, file/document upload) mean a new URL
is configuration, not code. A site that needs CAPTCHA/MFA is reported as "requires manual import";
it is never bypassed.

**Market Research Agent.** Admin-triggered with a scope (roles, topics, time window). It runs web
search and fetch, then extracts findings in which every claim cites at least one source URL with an
access date (uncited claims are dropped). It produces a structured report plus
**curriculum recommendations in `pending` status**. Approving a recommendation (`taxonomy.manage`)
may add or modify taxonomy entries. It never starts generation; that is always a separate,
deliberate Studio action.

**Intelligence engine.** Read-side queries and aggregations over approved interview questions,
clusters and research findings: frequency by topic, role and period (counted from evidence), trend
direction combining history *and* current research, and coverage gaps against published content.

## 8. Content generation & approval

Studio: choose domain → topics/subtopics → components → supporting intelligence → see a cost
estimate → start. This creates a batch with **one job per topic**, subject to configurable batch size
and budget limits. Each component is generated into a new `draft` version. Automated quality checks
then run: schema validity, sandboxed code execution, answer-key consistency (an evaluator model
re-solves the questions), duplicate detection, link checks, difficulty classification, and video
script length. Passing versions move to `under_review`.

A reviewer can edit, regenerate one component, compare versions, approve, or reject. Publishing
requires `content.publish`. Nothing in a batch publishes automatically. Students can only read
published versions of published topics.

**Pilot gate:** until an admin with `settings.manage` records the explicit "expansion approved"
decision (`platform_settings`), the Studio refuses to generate for topics not flagged `is_pilot`.
This enforces requirement 12 in code, not only in process.

## 9. User journeys (initial)

- **Student:** register → land on dashboard → profile/sessions (Phase 1). Later phases add
  explore domains → open topic → intuition → video → visualization → Python → interview questions →
  revision → assessment, with progress saved on every step and a "continue where I left off" card.
- **Admin:** log in → overview → manage students and cohorts → manage admins and roles → audit log
  (Phase 1). Later phases add configuring a source and credentials → test connection → run
  exploration → review extraction; run research → approve recommendations; Studio → review →
  publish; analytics → role rankings → student report.

## 10. Initial pilot content (proposal, to confirm before Phase 4)

The spec asks for the selection to be informed by interview intelligence and research, which do not
exist yet. This is a **provisional** batch, chosen for interview frequency in common AI/ML roles and
for strong interactive visualizations. It will be re-checked against Phase 3 output before any
generation runs.

| Domain | Subtopics | Signature visualization |
|---|---|---|
| Machine Learning | Linear Regression · Logistic Regression · K-Means Clustering | Draggable points + fitted line; sigmoid/decision boundary; clusters forming step by step |
| Deep Learning | Gradient Descent · Activation Functions · Neural Network Fundamentals (forward/backprop) | Loss-surface playground (learning rate, momentum); function/derivative explorer; live forward pass |
| Generative AI & LLMs | Tokenization & Embeddings · Attention & Transformers · RAG | Tokenizer playground + embedding space; attention heat-map; retrieval → context → answer pipeline |

Pilot evaluation before scaling: automated checks (above) plus a reviewer rubric scored 1–5 per topic
on technical correctness, clarity, interview relevance, visualization, code, video, assessment and
overall experience. An optional pilot cohort's assessment item statistics (difficulty and
discrimination) and feedback are also reviewed. Expansion only happens after the recorded green signal.

## 11. Open inputs needed from the product owner

Each is integrated through configuration when provided. Status as of 2026-10-27:

| # | Input | Status |
|---|---|---|
| 1 | Interview sources: URLs, auth types, credentials, confirmation that automated access is allowed | **Open** |
| 2 | LLM provider key and budget | **Decided:** OpenRouter. The key goes in `IPP_OPENROUTER_API_KEY` (not yet set). Recommended: a dedicated key with a weekly budget set in OpenRouter as the hard cap. |
| 3 | Web search API for market research | **Open** (OpenRouter's web-search plugin is a candidate, so no extra key would be needed) |
| 4 | TTS provider | **Decided:** OpenRouter text-to-speech, same key. Voice is chosen in Phase 4. |
| 5 | Email delivery for password resets | **Open.** Dev prints links to the API console. |
| 6 | Hosting | **Proposed** in §14, awaiting confirmation |
| 7 | Student onboarding | **Deferred (2026-10-27):** while the platform is being built and tested, students register with email + password (already implemented). NxtWave login is decided after testing, before real students join. The options are NxtWave's own login (needs SSO/OAuth from NxtWave's tech team) or our own password linked to a NxtWave ID (optionally checked against an admin-uploaded roster). Either is an additive change. |
| 8 | Data retention | **Decided:** permanent for activity logs and source records (see §4) |
| 9 | Branding | **Open.** Name candidates were offered. "AI/ML Interview Prep" is used until then (`frontend/src/brand.ts`). |

## 12. Assumptions

- Student self-registration is open (it can be switched to invite-only later).
- Email verification is deferred until an email provider is configured. Accounts are active on registration.
- One admin per person (no shared accounts). The first Super Admin is created from the CLI.
- English-only UI for now.
- Navigation only shows modules that actually work. Items are added as each phase ships, with no
  placeholder screens.
- AI spend weeks run Tuesday → Monday in India Standard Time, starting 2026-10-27 (the day the
  feature was requested). Both are settings (`IPP_USAGE_TRACKING_START`, `IPP_USAGE_TIMEZONE`).
  OpenRouter's own "weekly" figures use Monday-start UTC weeks, which is why the console shows our
  ledger's weeks plus OpenRouter's lifetime and cap figures, not OpenRouter's weekly number.

## 13. Phase status

| Phase | Scope | Status |
|---|---|---|
| 1 | Foundation, admin & student auth, RBAC, dashboards, student & admin management, audit log | **Done** (2026-10-27): 84 backend + 21 frontend tests, browser-verified desktop & mobile |
| 1.1 | OpenRouter client, AI spend ledger, weekly spend page (Settings → AI usage), permanent logs | **Done** (2026-10-27): 108 backend + 28 frontend tests, browser-verified. Live OpenRouter check pending the key. |
| 2 | Interview data sources, encrypted credentials, connectors, connection tests, imports | Next |
| 3 | Job queue + worker, exploration & research agents, intelligence DB, review | |
| 4 | Taxonomy, pilot content generation, learning pages, visualizations, Pyodide, videos, assessments | |
| 5 | Quality checks, review/publish UI, individual & bulk generation, pilot gate | |
| 6 | Progress tracking, attempts, analytics, role-readiness intelligence | |
| 7 | Hardening, performance, deployment, monitoring, backups, docs | |

## 14. Hosting plan (proposal for the free pilot, awaiting confirmation)

| Piece | Free option | Notes |
|---|---|---|
| Frontend | Vercel (Hobby) | `vercel.json` rewrites `/api/*` to the API, so the browser sees a single origin and the path-scoped session cookies work unchanged. Hobby is limited to non-commercial use. It is fine for internal testing; move to Vercel Pro or Cloudflare Pages before real students use it. |
| API + job worker | Render free web service (native Python runtime, no Docker) | Sleeps after 15 min idle, and the first request takes about a minute. The free tier has no background workers, so the worker runs inside the web process; jobs resume from the `jobs` table. The local disk is wiped when it sleeps, so nothing is kept on disk. |
| Database | Neon free (0.5 GB, scales to zero) | **Not** Render's free Postgres, which is deleted after 30 days and conflicts with permanent retention. |
| Media (audio/video) | Cloudflare R2 free (10 GB, no egress fees) | Needed from Phase 4. |
| Backups | Nightly `pg_dump` to R2 from a scheduled GitHub Action | Permanent retention needs an off-site copy. |

Deployment tasks (Phase 7, or earlier if hosting moves forward):
- Add `vercel.json` and a Render blueprint.
- Trust the proxy's `X-Forwarded-For`, so per-IP rate limits see the student's IP rather than Vercel's.
- Set `IPP_ENVIRONMENT=production` and `IPP_COOKIE_SECURE=true`.
- Store secrets in each host's environment settings.

Moving to the real domain later means pointing DNS and upgrading plans to remove the sleep; no code
changes are needed.
