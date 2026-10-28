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
| Background jobs | **Postgres-backed job queue** (`jobs` table, `FOR UPDATE SKIP LOCKED`) + a worker (implemented in Phase 2, `app/jobs/runner.py`) | Agent and generation jobs are low-volume and long-running, and they need durable status, progress, history and retry, which means a table anyway. This avoids running Redis/Celery for no extra value. The worker runs as a thread inside the API by default (`IPP_EMBEDDED_WORKER`), or as its own process (`python -m app.cli run-worker`). Swap in a broker only if throughput ever requires it. |
| Frontend | **React + TypeScript + Vite**, React Router, TanStack Query, Tailwind CSS v4 | A SPA fits a cookie-authenticated API on the same origin. TanStack Query handles caching and deduplication, which avoids redundant API calls. Tailwind provides a consistent design system with small CSS output. Admin and student code are lazily loaded, separate chunks. |
| Visualizations | Hand-built SVG/Canvas React components (D3 helpers where useful) | Interactive, parameter-driven playgrounds such as gradient descent, K-Means and attention. Static images are not acceptable. |
| Code playground | **Pyodide (CPython in WebAssembly) in a Web Worker** in the student's browser (implemented in Phase 4, `frontend/src/lib/pyodide.ts`) | Student code never runs on our servers, which satisfies the isolation requirement at zero server cost. Each run gets a fresh namespace and a 30-second limit (the worker is terminated). Lab code is checked before publishing by running it the same way in a reviewer's browser; the server compares the output with the expected output and records the check (see §8). |
| AI layer | **OpenRouter** through one client (`app/ai/openrouter.py`) + per-task model routing + usage ledger | One key reaches many vendors' models, so each task can use a different model (cheap ones for classification, stronger ones for generation and evaluation). Models are configuration, not code. Every call records its USD cost in `ai_usage_events` (implemented 2026-10-27). |
| Video | A scene player, not rendered video files (Phase 4) | Each scene is an animated SVG figure, a big caption and narration. Narration is OpenRouter text-to-speech (`POST /audio/speech`, same key, same cost ledger), one clip per scene. Without recorded audio, students get captions, auto-advance and an optional device voice. |
| Media storage | Narration clips in Postgres (`media_assets`, at most 3 MB per clip) for the pilot | Kept with the version they belong to and served only through permission-checked endpoints. Move to an S3-compatible bucket (§14) when media volume grows. |

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
`login_events`, `ai_usage_events`, `raw_source_records` and `job_events`, and any DELETE on
`interview_sources` and `jobs` (their status changes, but rows are never deleted). Phase 3
extraction and research records get the same treatment. Accounts are disabled, never deleted, so
log references stay valid.

**Sources & jobs (Phase 2, implemented 2026-10-27)**
- `interview_sources`: name (unique among active sources), base URL, connector type, sign-in
  method, non-secret `config` / `auth_config` (JSONB), incremental `sync_state`, enabled flag,
  connection status + message, last tested / attempted / successful fetch. "Remove" archives the
  source (`archived_at`) and deletes its credentials; its records stay.
- `source_credentials`: one Fernet token per source, the id of the key that encrypted it, and the
  *names* of the stored fields only. Secrets are never returned by any API.
- `jobs` (kind, status, source, payload, result counters, progress, attempts, heartbeat, cancel
  flag, error, triggered by) and `job_events` (the execution log).
- `raw_source_records` (source, job, external id, revision, URL, title, content type, extracted
  text, content hash, published at, meta). A changed document is stored as a new revision, never
  overwritten; unchanged content is skipped. This makes fetching incremental and auditable.

**Taxonomy (Phase 3, implemented 2026-10-27)**
- `domains` and `topics` (`parent_id` makes a subtopic; global slugs such as
  `machine-learning/regression`; `is_pilot`; archived, never deleted). The starting set is the
  requirements' §9 list, seeded once by `python -m app.cli seed-taxonomy`.

**Intelligence (Phase 3, implemented 2026-10-27)**
- `record_extractions` (append-only): one row per attempt to read a record. A record with an
  `extracted` or `not_interview` attempt is never sent to the model again.
- `interview_experiences` → `interview_questions` (actual questions): company, role, round, exact
  date or period, location, verbatim `original_text` (never edited), question type, difficulty,
  topic, `grounded` (found word-for-word in the record), review status, `duplicate_of`, and
  provenance links to source, raw record and job.
- Duplicates form clusters through `duplicate_of` (exact normalised text, then ≥ 0.9
  similarity). Frequency is always *computed* as the distinct approved records in a cluster;
  it is never stored.
- `research_reports` → `research_sources` (URL, title, site, excerpt, access time) and
  `research_findings` → `finding_evidence` (source, quote, `quote_verified`). All append-only.
- `curriculum_recommendations` (pending / approved / rejected / deferred, decided by and at, and
  the topic an approved "add topic" created) and `research_questions` (research-derived
  practice questions, kept apart from actual interview questions).
- `ai_usage_events.job_id` ties every AI call to the run that made it, so each run shows its cost.

**Learning content (Phase 4, implemented 2026-10-27, migration 0005)**
- `content_items`: one per topic × component (lesson, playground, video, python, interview, quiz,
  revision), pointing at `published_version_id`. Never deleted.
- `content_versions`: number, body (JSONB in canonical form, validated by the component's schema in
  `app/content/schemas.py`), lifecycle status, origin (`starter`, `ai_generated`, `edited`), the
  version it was based on, model, job, author, reviewer, review note, published time. A trigger
  makes the body immutable and rejects deletes: an edit or a restore is always a new version.
- `code_checks` (append-only): a run of a Python lab's exact program (SHA-256 of its code), its
  output, error, runtime and duration. The server decides `passed`.
- `media_assets`: narration audio per scene of a video version. Never deleted.
- `platform_settings`: key/value decisions, starting with `content_expansion_approved`.
- `jobs` gained `topic_id` and `batch_id`, so generation runs and their AI cost belong to a topic.
- Interview questions inside content carry `origin` ∈ {ai_generated, admin_created,
  actual_interview, research_derived} and a `source_ref`. The schema requires a `source_ref` for
  actual and research-derived questions, and the generator replaces their wording with the approved
  record's exact text (or drops an unknown reference). **Content bodies have no company field.**
  Students read content only through `app/api/student/learn.py`, which serves published versions
  through student schemas (`app/schemas/learn.py`): `origin` and `source_ref` become a label
  ("Practice question", "Asked in real interviews", "In demand right now") and the role, never a
  company or source. (This replaces the separate `practice_questions` table first planned here.)

**Later (Phases 5–6):** `job_roles`, `topic_role_relevance`, content ↔ intelligence links,
automated quality-check reports.

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

**Interview Exploration Agent (implemented in Phase 3, `app/agents/exploration.py`).** It runs only
on an explicit admin trigger (`agents.run`); nothing in a login or page view can enqueue it.
1. The admin selects sources and limits (records and USD per source). This creates one job per
   source. At most one fetch or exploration runs per source at a time, enforced by the database.
2. Optionally, the job first fetches new records (reusing the Phase 2 fetch).
3. It reads the latest revision of every record not yet read, one structured-output call per
   record (`IPP_MODEL_EXTRACTION`, strict JSON schema). An invalid reply gets one repair
   attempt; after that the record is marked failed and retried next run. A rejected key or no
   credit stops the run.
4. Safeguards are enforced in code, not only in the prompt:
   - questions must be found (near) word-for-word in the record, or they are flagged;
   - a company not written in the record is dropped;
   - an exact date needs its day, month and year in the record;
   - topics must be existing slugs;
   - the record is fenced as untrusted data.
5. Duplicate detection: exact normalised text, then string similarity within the topic.
6. Everything lands as `pending_review`. Reviewers (`intelligence.review`) approve, reject, re-topic,
   merge duplicates and correct interview details, all audited. Only approved questions count.
7. The run stops at its spending limit (checked before every call) and reports what is left.

**Source connectors (implemented in Phase 2, `app/sources/`).** Each connector is a class in
`CONNECTORS` with a strict Pydantic settings model and form descriptions (`FieldSpec`) that the
console renders, so a new URL is configuration and a new *kind* of source is one class.
- **Website pages:** start pages, optional CSS selectors for links to follow (same site only),
  "next page" pagination and main content; skips pages already fetched.
- **JSON API:** endpoint, items path, id/title/link/date fields, pagination by page number, offset,
  next-page URL or cursor, and an optional "changed since" parameter for incremental runs.
- **RSS / Atom feed:** optionally reads each post's full page.
- **File import:** CSV, JSON/JSONL, PDF, Word (.docx), text, Markdown and saved HTML. Files can be
  imported into *any* source; this is the authorised route when a site blocks automation.

Sign-in methods are none, HTTP Basic, bearer token, API key in a header or query parameter, and a
website login form (hidden CSRF fields are carried over). All outbound requests go through
`SafeHttp` (`app/sources/http.py`):
- It refuses private and internal addresses on every hop (SSRF protection).
- It sends credentials only to the source's own site.
- It caps size and time, spaces out requests, and retries transient failures on GETs.
- It honours robots.txt when crawling pages.
- It reports CAPTCHAs, bot checks and one-time codes as "manual import"; these are never bypassed.

Changing a source's site (or login page) clears its stored credentials, so an admin who may edit
sources but not credentials cannot redirect secrets elsewhere.

**Market Research Agent (implemented in Phase 3, `app/agents/research.py`).** It is
admin-triggered with a scope: roles, an optional focus, a region, a time window, sources per
search and a spending limit.
1. It runs one OpenRouter web search per role (`plugins: [{id: "web", engine}]`,
   `IPP_RESEARCH_SEARCH_ENGINE`, default Exa), and collects the cited URLs with their excerpts.
2. A structuring call (`IPP_MODEL_RESEARCH`, strict schema) turns the numbered sources into
   findings, recommendations and practice questions.
3. These are kept only when backed:
   - a finding must cite a retrieved source;
   - quotes are checked against the excerpt (`quote_verified`);
   - recommendations and questions must rest on kept findings;
   - "add topic" needs a real domain and a new name.
4. Recommendations wait as `pending`. Approving one (`taxonomy.manage`) records the decision.
   For "add topic" it creates a non-pilot topic. It never generates content.

**Intelligence engine (implemented).** For each topic, the console shows approved interview
evidence (questions, distinct records, roles) beside the latest research trend. A transparent label
says which kinds of evidence point at the topic (asked & rising, rising in market, asked, declining,
no evidence); there is no opaque score, and frequency is never inferred from unapproved data.
Coverage gaps against published content arrive with Phase 5.

## 8. Content generation & approval

Implemented in Phase 4 (`app/content/`, `app/api/admin/content.py`, console: Content studio).

**Generation.** An admin with `content.generate` picks topics, components, whether to use approved
intelligence, and a spending limit per topic. This creates a batch with **one job per topic**
(`IPP_MODEL_CONTENT`, strict JSON schema per component). Each component becomes a new `draft`
version; a component that fails is reported in the run log and the rest continue. The run stops at
its spending limit. The playground is only generated for topics that have an interactive widget.
Intelligence is passed as approved actual questions (with role and round), approved
research-derived questions and cited findings, never a company.

**Narration.** `content.generate` can narrate a video version with one of the configured voices
(`IPP_NARRATION_VOICES`). One clip per scene is stored with that version, with its cost in the ledger.

**Review lifecycle.** draft → under_review → approved → published, plus send back, reject,
unpublish and archive. Each step needs a specific permission (submit: generate or review; send
back and reject: review; approve, publish, unpublish and archive: publish). Every step is audited.
Publishing a version archives the previously published one. Bulk submit, approve and publish
per topic report what they skipped and why. Reviewers can preview exactly what students will see,
edit the JSON (validated by the server, saved as a new draft), compare any two versions line by
line, and restore an older version as a new draft.

**Code gate.** A Python lab can only be published after a passing code check of its exact
program. The reviewer's browser runs it in Pyodide; the server compares the output with the
lab's expected output and records the check.

**Students** read only published versions, and a topic appears once its lesson is published.

**Pilot gate:** until an admin with `settings.manage` records the explicit "expansion approved"
decision (`platform_settings`), generation is refused for topics not flagged `is_pilot`, both
when a run is requested and again when the job starts. Changing which topics are pilot topics
also needs `settings.manage`. This enforces requirement 12 in code, not only in process.

**Not yet (Phase 5):** automated quality checks beyond schema validation and the code gate
(an evaluator model re-solving quiz answers, duplicate and difficulty checks, video script
timing), a server-side code sandbox for generated labs, coverage gaps against intelligence, and
the reviewer rubric.

## 9. User journeys (initial)

- **Student:** register → dashboard → profile/sessions (Phase 1). Phase 4 adds Explore → topic →
  Learn (swipeable cards with animated figures) → Play (interactive playground with "try this"
  tasks) → Watch (narrated scenes) → Code (run real Python in the browser) → Interview → Quiz →
  Revise. Phase 6 adds saved progress, quiz attempts and a "continue where I left off" card.
- **Admin:** log in → overview → manage students and cohorts → manage admins and roles → audit log
  (Phase 1). Later phases add configuring a source and credentials → test connection → run
  exploration → review extraction; run research → approve recommendations; Studio → review →
  publish; analytics → role rankings → student report.

## 10. Pilot content (confirmed 2026-10-27)

The product owner chose two domains with three subtopics each (2026-10-27). Each has all seven
components and its own playground:

| Domain | Subtopic | Playground |
|---|---|---|
| Machine Learning | Supervised Learning | k-NN classifier: add points, change k, drag a query star, train vs test accuracy |
| Machine Learning | Unsupervised Learning | k-means step by step, new starts, elbow chart |
| Machine Learning | Regression | Fit a line by hand vs least squares, residuals and squared errors, MSE and R² |
| Deep Learning | Neural Network Fundamentals | Train a small network on XOR, circle or blobs; watch weights, loss and decision map |
| Deep Learning | Activation Functions | Five functions with slopes, and how gradients shrink across layers |
| Deep Learning | Optimizers | GD, Momentum and Adam on a stretched loss bowl, step counts compared |

**Starter content.** No AI key or interview records were available yet, so the development
assistant (Claude Opus 5.5) wrote starter drafts for all 42 components (`app/content/starter/`).
They are imported as `starter` drafts by `python -m app.cli seed-pilot-content`, labelled as such,
and go through the same review and publishing as any AI draft. Every lab's expected output was
produced by running it. Their interview questions are practice questions (`ai_generated`); none
claims to come from a real interview. `seed-pilot-content --refresh` adds a new draft when the
starter content changes later.

Pilot evaluation before scaling: automated checks (above) plus a reviewer rubric scored 1–5 per topic
on technical correctness, clarity, interview relevance, visualization, code, video, assessment and
overall experience. An optional pilot cohort's assessment item statistics (difficulty and
discrimination) and feedback are also reviewed. Expansion only happens after the recorded green signal.

## 11. Open inputs needed from the product owner

Each is integrated through configuration when provided. Status as of 2026-10-27:

| # | Input | Status |
|---|---|---|
| 1 | Interview sources: URLs, auth types, credentials, confirmation that automated access is allowed | **Open.** The platform side is ready (Phase 2): admins add sources and credentials in the console, never in chat or code. |
| 2 | LLM provider key and budget | **Decided:** OpenRouter. The key goes in `IPP_OPENROUTER_API_KEY` (not yet set). Recommended: a dedicated key with a weekly budget set in OpenRouter as the hard cap. |
| 3 | Web search API for market research | **Default chosen:** OpenRouter web search (Exa engine) on the same key, about $0.007 per search. Change with `IPP_RESEARCH_SEARCH_ENGINE`. |
| 4 | TTS provider | **Decided:** OpenRouter text-to-speech (`microsoft/mai-voice-2.1-flash`), same key. Voices: `en-IN-Priya` and `en-IN-Dhruv`; the reviewer picks one per narration (`IPP_NARRATION_VOICES`). |
| 5 | Email delivery for password resets | **Open.** Dev prints links to the API console. |
| 6 | Hosting | **Proposed** in §14, awaiting confirmation |
| 7 | Student onboarding | **Deferred (2026-10-27):** while the platform is being built and tested, students register with email + password (already implemented). NxtWave login is decided after testing, before real students join. The options are NxtWave's own login (needs SSO/OAuth from NxtWave's tech team) or our own password linked to a NxtWave ID (optionally checked against an admin-uploaded roster). Either is an additive change. |
| 8 | Data retention | **Decided:** permanent for activity logs and source records (see §4) |
| 9 | Branding | **Open.** Name candidates were offered. "AI/ML Interview Prep" is used until then (`frontend/src/brand.ts`). |

## 12. Assumptions

- Student self-registration stays open to anyone with the link until the project is complete
  (product owner, 2026-10-27). NxtWave login is decided after testing.
- Raw source records store the text extracted from a page or file. For uploads, the original file's
  name, size and SHA-256 are kept, but not the file itself (media storage arrives in Phase 4).
- robots.txt governs crawling (website pages, full-page feed reads). APIs and feeds are governed by
  the provider's terms, which the admin confirms when adding the source.
- Uploads are limited to 10 MB per file. Scanned PDFs without a text layer aren't supported yet (no
  OCR).
- Email verification is deferred until an email provider is configured. Accounts are active on registration.
- One admin per person (no shared accounts). The first Super Admin is created from the CLI.
- English-only UI for now.
- Until Phase 6, quiz answers, playground tasks and code edits live only in the open page; nothing
  about a student's learning is saved yet, and the student app doesn't claim it is.
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
| 2 | Interview data sources, encrypted credentials, connectors, connection tests, imports, job queue + worker | **Done** (2026-10-27): 227 backend + 37 frontend tests, browser-verified (desktop and mobile) against real public sites with SSRF protection on |
| 3 | Exploration & research agents, taxonomy, intelligence DB, review, run history and costs | **Done** (2026-10-27): 292 backend + 43 frontend tests. Browser-verified with synthetic records and a simulated OpenRouter, in a throwaway database. Live AI runs are pending the OpenRouter key and real interview records. |
| 4 | Taxonomy editing, pilot content, generation, review & publishing, learning pages, playgrounds, Pyodide, narrated videos, quizzes | **Done** (2026-10-27): 363 backend + 100 frontend tests. Browser-verified (desktop and mobile) in a throwaway database with a simulated OpenRouter: review → code check → publish, narration, generation, edit validation, compare, taxonomy, the pilot gate, every student section and all six playgrounds, and that student APIs leak no provenance. Live generation and narration are pending the OpenRouter key. |
| 5 | Automated quality checks, server-side lab sandbox, coverage gaps, reviewer rubric, regenerate one component | Next |
| 6 | Progress tracking, attempts, analytics, role-readiness intelligence | |
| 7 | Hardening, performance, deployment, monitoring, backups, docs | |

## 14. Hosting plan (proposal for the free pilot, awaiting confirmation)

| Piece | Free option | Notes |
|---|---|---|
| Frontend | Vercel (Hobby) | `vercel.json` rewrites `/api/*` to the API, so the browser sees a single origin and the path-scoped session cookies work unchanged. Hobby is limited to non-commercial use. It is fine for internal testing; move to Vercel Pro or Cloudflare Pages before real students use it. |
| API + job worker | Render free web service (native Python runtime, no Docker) | Sleeps after 15 min idle, and the first request takes about a minute. The free tier has no background workers, so the worker runs inside the web process; jobs resume from the `jobs` table. The local disk is wiped when it sleeps, so nothing is kept on disk. |
| Database | Neon free (0.5 GB, scales to zero) | **Not** Render's free Postgres, which is deleted after 30 days and conflicts with permanent retention. |
| Media (audio/video) | Cloudflare R2 free (10 GB, no egress fees) | Narration clips live in Postgres for the pilot; move them to R2 when volume grows. |
| Backups | Nightly `pg_dump` to R2 from a scheduled GitHub Action | Permanent retention needs an off-site copy. |

Deployment tasks (Phase 7, or earlier if hosting moves forward):
- Add `vercel.json` and a Render blueprint.
- Trust the proxy's `X-Forwarded-For`, so per-IP rate limits see the student's IP rather than Vercel's.
- Set `IPP_ENVIRONMENT=production` and `IPP_COOKIE_SECURE=true`.
- Store secrets in each host's environment settings. Set `IPP_CREDENTIALS_KEYS` to a production key,
  not the development one, and keep a copy somewhere safe: without it, stored source credentials
  must be entered again.
- The job worker runs inside the API process (Render's free tier has no background workers). A job
  interrupted by a restart is marked failed after 10 minutes without a heartbeat and can be
  started again.

Moving to the real domain later means pointing DNS and upgrading plans to remove the sleep; no code
changes are needed.
