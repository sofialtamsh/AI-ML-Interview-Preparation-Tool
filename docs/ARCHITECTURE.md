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
| Interview practice | Browser `MediaRecorder` + OpenRouter speech-to-text (`POST /audio/transcriptions`) + a feedback model (Phase 4.1) | The student's video is recorded and replayed in the browser only; just the voice (16 kHz mono WAV, converted in the browser) is uploaded, transcribed, scored and then erased. No video storage, no face analysis, nothing to secure beyond a transcript. |
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

**Interview practice (Phase 4.1, implemented 2026-10-28, migration 0006)**
- `practice_attempts`: student, topic, the published interview version and question index it
  answered (versions are immutable), a snapshot of the question, status (queued → processing →
  completed / no_answer / failed), duration measured from the WAV, the audio (erased when
  processing ends, whatever the outcome), transcript, delivery numbers, feedback, score, a
  user-facing error, the models used (admin-only), and `deleted_at`. A student's delete erases the
  transcript, delivery and feedback; the row stays (a trigger rejects DELETE) so spend and the
  daily limit stay accurate.
- `ai_usage_events` gained `triggered_by_student_id` and `practice_attempt_id`.
- `platform_settings["practice_feedback"]`: `{enabled, daily_limit}` (default on, 10 a day).

**Content quality (Phase 5, implemented 2026-10-28, migration 0007)**
- `content_quality_reviews` (append-only): an AI reviewer's report on one version: model, summary,
  rubric scores, issues (only those whose quote is really in the content), the quiz answer-key
  check, how many issues were dropped, who asked, the job (and so the cost).
- `content_ratings` (append-only): a reviewer's 1–5 scores on the pilot rubric for one version,
  with an optional note; an admin's latest row counts.
- Job kind `content_review`. Generation jobs record `generated_components` and
  `failed_components`, so a retry runs only what didn't finish, in the same batch.
- Automated checks aren't stored: they're computed in code each time (free and always current).

**Later (Phase 6):** `job_roles`, `topic_role_relevance`.

**Learning & performance (Phase 6, part A implemented 2026-10-28, migrations 0008–0009)**
- `learning_events` (append-only): what a student did, per topic and section: opened, finished,
  cards seen, playground task tried, video scene reached, code run (ok / matched), interview answer
  recorded, and active time (`active_time`, seconds credited). Validated against the published
  content.
- `topic_progress` (one row per student × topic, never deleted): each published section's status
  (started / done, with details such as cards seen or tasks tried), last section, first and last
  visit, `completed_at`, and `active_seconds` (time spent on the topic).
- `quiz_attempts` → `quiz_responses` (append-only): graded on the server against the published
  quiz version; a retake is a new attempt, never an overwrite. Each response keeps the choice,
  correctness, difficulty and kind.
- Mastery isn't stored: it is computed from the last three quiz attempts and the last five
  interview-practice scores of each topic (`practice_attempts`).
- **Part B (next):** `role_evaluation_frameworks` (versioned, transparent factor weights and
  minimum-evidence thresholds), `student_role_evaluations` (measured metrics kept separate from the
  AI narrative, readiness band including `insufficient_data`), `evaluation_overrides` (admin
  challenge/override with reason), and trend snapshots.

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
Each topic's page in the Content studio shows which approved interview questions its interview
prep uses (Phase 5).

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
The console says so on each topic page (and marks topics hidden for want of a lesson in the
studio), listing the tabs students currently see.

**Pilot gate:** until an admin with `settings.manage` records the explicit "expansion approved"
decision (`platform_settings`), generation is refused for topics not flagged `is_pilot`, both
when a run is requested and again when the job starts. Changing which topics are pilot topics
also needs `settings.manage`. This enforces requirement 12 in code, not only in process.

**Quality checks (Phase 5, `app/content/quality.py`, `app/content/review.py`,
`app/api/admin/content_quality.py`; console: each version's Quality tab).**
- *Automated checks* are free and run in code every time a version is opened:
  - every component: no company name from interview records anywhere in the text (error); no links
    (warning);
  - interview prep: real-interview and research-derived questions still match an approved record
    word for word (error); no near-duplicate questions, within the set or against other topics'
    published questions (warning); a difficulty mix (warning);
  - quiz: duplicates, difficulty mix, and an answer key that isn't guessable (70 % or more of
    answers on one option is a warning);
  - video: no scene with more narration than it can show in captions-only mode (warning) and
    which scenes have narration audio;
  - Python lab: the code parses, imports only allowed modules that are listed in `packages`, never
    calls `eval`/`exec`/`open`/`__import__` or dunder escapes (errors), uses fixed seeds (warning),
    and whether its code check passed;
  - playground: the widget is the topic's (error).
  Errors block publishing, alongside the code gate; warnings are for the reviewer. Running these
  over the starter content found real problems: three quizzes had most answers on option B, which
  was fixed.
- *AI review* (`IPP_MODEL_REVIEW`, default `google/gemini-3.8-flash`, a different vendor from the
  writer) is a job an admin with `content.review` or `content.publish` starts, with a spending
  limit. It scores factual correctness, clarity, maths consistency, topic and interview relevance,
  difficulty labels and one component-specific criterion, and lists issues with exact quotes. Code
  drops any issue whose quote isn't in the version. For a quiz it first answers every question
  *without* the key, and code compares its picks with the key. Reports are labelled as advice, never
  verification, and change nothing.
- *Reviewer ratings*: reviewers score a version 1–5 on the pilot rubric (technical correctness,
  educational clarity, interview relevance, overall student experience, plus visualization,
  Python, video, assessment, answer or revision quality for that component).
- *Revise with AI*: from any version, an admin with `content.generate` asks for a new draft that
  follows their instructions and/or the latest AI review (including answer-key disagreements). It
  is a generation job (same pilot gate, spending limit and review), based on that version.
- *Retries*: a content run that didn't fully succeed can be retried; generation reruns only the
  components it didn't produce, narration only the missing scenes, in the same batch.
- *Pilot evaluation* (Content studio): for every pilot topic × component, what's published, check
  errors, AI review average and reviewer rating of what students see (or the latest draft), with
  totals. The expansion dialog shows the same summary before the green signal.
- *Interview coverage & spend* (each topic page): AI spend across the topic's runs, and which
  approved interview and research-derived questions the interview prep uses.

**Decided against for now:** running lab code on the server. The reviewer's browser runs it in
Pyodide (WebAssembly, no server access), the server judges the output, and the static checks above
reject unsafe code. A server sandbox would add risk (AI-written code influenced by scraped text)
and hosting cost for no extra assurance. Revisit if labs ever need to run without a reviewer.

## 8.1 Interview practice (Phase 4.1)

Implemented 2026-10-28 (`app/practice/`, `app/api/student/practice.py`, `app/api/admin/practice.py`,
`frontend/src/learn/practice/`, `frontend/src/student/practice/`). Requested by the product owner.

**Student flow.** In a topic's Interview section, each question opens with "Answer it like the real
thing". The student picks camera + mic or voice only, gets a 3-2-1 countdown, and answers with the
question shown over the camera view. A timer bar marks the 1–2 minute sweet spot; recording stops at
3 minutes (`IPP_PRACTICE_MAX_ANSWER_SECONDS`). The camera switches off when recording stops. They
can rewatch, retake, save the video to their device, or ask for AI feedback. The strong answer,
"what the interviewer wants" and the follow-ups unlock after the student's first take of that
question: any attempt with feedback, or a recording made in that browser (remembered locally,
since takes without feedback aren't saved). If the camera or mic can't be used, a "Can't record
right now?" link shows the answer anyway, so nobody is locked out. This is a study nudge, not a
secret: published answers are part of the student API. Earlier tries are listed with score
and verdict, and can be reopened or deleted. Recording works without AI (key missing, feedback
switched off, or the daily limit reached); the student is told why feedback isn't available.

**Privacy.** The video never leaves the browser. A second recorder captures only the microphone
track, which the browser converts to 16 kHz mono WAV. The server reads the length from the WAV
itself (3 s to the limit, size capped). The audio is erased as soon as processing ends. Students
see only their own attempts (every query is scoped to the session's student; another student's
attempt is a 404), never model names. Admins see counts, average score and cost, not transcripts.

**Processing.** Uploading creates a queued attempt; dedicated practice worker threads
(`IPP_PRACTICE_WORKERS`, default 2, separate from the admin job worker so a long content run never
delays students) claim it with `FOR UPDATE SKIP LOCKED`:
1. Speech-to-text (`IPP_MODEL_TRANSCRIPTION`, default `openai/whisper-large-v3`, English), asking
   for timed segments and falling back to plain text if the provider rejects that (400, unbilled).
2. Delivery measured in code: words per minute over the time actually spoken, filler words
   (um/uh/hmm/basically/actually/"you know"/"I mean"; a floor, since transcribers drop some),
   longest pause, number of pauses of 3 s or more, and the pause before speaking.
3. Fewer than 12 words: `no_answer`, nothing is sent for feedback.
4. Feedback (`IPP_MODEL_FEEDBACK`, default `anthropic/claude-sonnet-5.5`) through `structured_chat`
   with the `AnswerFeedback` schema, graded against the question's reviewed answer, "what the
   interviewer wants" and its follow-ups. The prompt says to judge meaning, not transcription
   slips; to never comment on accent, voice, appearance or grammar; and to ignore instructions
   inside the transcript.
5. Checked in code: strengths and mistakes whose quote isn't in the transcript are dropped; the
   follow-up must be one of the question's own; the overall score is computed here, never taken
   from the model: technical accuracy 35 %, depth & coverage 30 %, structure 15 %, communication
   20 %, each 1–5, mapped to 0–10. Verdicts: 8+ Interview-ready, 6+ Almost there, 4+ Getting
   there, else Keep practising. A technical-accuracy score of 2 or less caps the verdict at Getting
   there; an off-topic answer is capped at 2/10 and labelled "Didn't answer the question".
6. Every call goes through `OpenRouterClient` with features `practice_transcription` and
   `practice_feedback`, tagged with the student and the attempt.

Provider errors become a friendly "busy, try again" or "temporarily unavailable" message; a failed
attempt doesn't count toward the daily limit. Attempts stuck in processing for 10 minutes are
failed and their audio erased.

**Limits.** Admins with `settings.manage` switch feedback on or off and set answers per student per
day (1–50) in Settings → AI usage, which also shows last week's answers, students, average score and
cost (`ai_usage.view`). Changes are audited (`practice.settings_changed`). Uploads are also
rate-limited to six a minute per student (not per IP: a classroom can share one address).

**Section order.** Learn → Play → Watch → Code → **Quiz → Interview** → Revise: the quiz checks
understanding, then the student says it out loud.

**Not yet:** judging eye contact or body language (unreliable and prone to bias, so deliberately
left out), follow-up rounds where the AI asks the next question, and practice progress over time
(Phase 6 analytics).

## 8.2 Learning progress and analytics (Phase 6, part A)

Implemented 2026-10-28 (`app/progress/`, `app/api/student/progress.py`, `app/api/admin/analytics.py`,
the student dashboard, the admin student profile and Analytics page).

**Saved as students learn.** The topic page records a `section_opened` event for each section and
each section reports what the student did; nothing is kept only in the browser. A section is done
when the student has seen every lesson card, tried every playground task, watched the video to the
end, run the lab and got the expected output, submitted the quiz, recorded answers to at least half
the interview questions, or opened the cheat sheet. A topic is complete when every published
section is done. The strong-answer unlock (Phase 4.1) now comes from the student's saved takes, so
it follows them across devices.

**Completion vs mastery.** Completion is the sections a student went through; mastery is how well
they did: the average of their last three quiz attempts and last five interview-practice scores
(quiz 60 %, practice 40 % when both exist). Bands: strong (75+), developing (50+), needs work, or
"not enough evidence" with no quiz or scored practice. A great quiz doesn't complete a topic, and a
completed topic isn't called mastered.

**Student dashboard.** Streak (consecutive active days, India time), path completion, quiz average,
answers practised; continue where you left off (with the next unfinished section); completion per
domain; every topic with completion and mastery; strengths and weak spots; recommended next (the
next unstarted topic, then the weakest topic); recent quiz scores; interview-practice scores. The
Explore cards show each topic's progress.

**Time spent learning.** While a topic page is open, the browser counts time when the tab is
visible and the student has used the mouse, keyboard, scroll or touch in the last two minutes, or a
video or audio is playing. It sends what it has counted about once a minute, when the tab is
hidden and when the student leaves (`POST /api/student/progress/time`, at most 120 s per report,
12 reports a minute). The server never credits more than the time that has passed since the
student's previous report, plus 10 s for network delay, so a second tab or a tampered browser
can't inflate it. Reports are serialised per student with a Postgres advisory lock. Time doesn't
complete sections, and it doesn't appear in the admin activity timeline.

**Admins** (`students.view`): the student directory shows learning per student (topics done, quiz
and practice averages, last learning activity) and flags students who need attention: *inactive*
(no learning for 14 days, or none a week after registering) and *struggling* (quiz average under
50 % over two or more attempts, or practice under 4/10 over two or more answers), with a filter. Each
student's profile has a Learning section: progress per topic with mastery and time spent, time
learning in total and in the last 7 days, every quiz attempt with a side-by-side comparison of two
attempts, practice scores (never transcripts) and recent activity, with a link to Analytics
filtered to the student.

**Admin Overview** (`analytics.view`): a Learning section for the last 30 days: active learners,
average path completion, learning time, quiz average, interview-practice average, how many need
attention (linking to the filtered directory), completion by domain, and completion of the
most-started topics. It reuses the Analytics report, so both pages show the same numbers.

**Analytics** (`analytics.view`, new nav entry): students, active learners, new registrations,
average path completion (every student's done sections out of the live sections in scope,
averaged over all students in scope, so those who haven't started count as 0 %), learning time
(total and per learner), quiz attempts and average, practice answers and average, live topics,
and how many need attention;
registrations per day and active learners per week (every day and week in the range, zeros
included); quiz score distribution; weak topics (lowest quiz average with 3+ attempts); completion
rate, performance and learning time per topic and domain; cohorts. Filters: date range (up to a
year), cohort, domain, topic, and one student (a search box). The student filter needs
`students.view` as well, in the UI and in the API (403 without it); with it, cohorts aren't
compared and a deactivated student can still be picked. **Export** (`analytics.export`): every
student's learning summary as CSV, including learning time, audited (`analytics.students_exported`)
and safe against spreadsheet formula injection.

## 9. User journeys (initial)

- **Student:** register → dashboard → profile/sessions (Phase 1). Phase 4 adds Explore → topic →
  Learn (swipeable cards with animated figures) → Play (interactive playground with "try this"
  tasks) → Watch (narrated scenes) → Code (run real Python in the browser) → Quiz → Interview
  (record an answer, get interviewer-style feedback) → Revise. Phase 6 saves progress and quiz
  attempts to the account, and the dashboard shows progress, mastery, a "continue where I left off"
  card and recommendations.
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
- Learning progress and quiz attempts are saved to the student's account (Phase 6). Edited lab code
  isn't saved; only whether a run matched the expected output. Progress events are reported by the
  browser, so completion is a learning aid; quiz scores are graded on the server.
- Practice answers are assumed to be in English (the transcriber is told `en`). Practice videos are
  never uploaded; a student who wants to keep one saves it to their device.
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
| 4.1 | Interview practice: record a spoken answer, transcription, interviewer-style feedback, admin switch and daily limit; Quiz before Interview | **Done** (2026-10-28): 385 backend + 112 frontend tests. Browser-verified (desktop camera, mobile voice only) in a throwaway database with a simulated OpenRouter and the browser's fake camera and mic; the uploaded audio was checked to be 16 kHz mono WAV of the recorded length. Live transcription and feedback are pending the OpenRouter key. |
| 5 | Content quality checks and the publish gate, AI review (quiz re-solved without the key), reviewer rubric, revise with AI, retry what failed, pilot evaluation, interview coverage and topic spend | **Done** (2026-10-28): 415 backend + 122 frontend tests. Browser-verified in a throwaway database with a simulated OpenRouter: checks, AI review with a flagged answer key and a dropped invented quote, rating, revision to a new draft, a failed video retried alone, pilot evaluation and the expansion summary, audit labels, mobile. Live AI review is pending the OpenRouter key. |
| 6A | Saved progress and quiz attempts, completion vs mastery, student dashboard, admin student learning view and attention flags, Analytics with filters and CSV export; then the gaps against the spec: learning on the admin Overview, a student filter in Analytics, time spent learning | **Done** (2026-10-28): 438 backend + 142 frontend tests. Browser-verified in a throwaway database (desktop and mobile): a student finished sections, took quizzes and recorded an answer; progress followed them to a second device; the dashboard, Explore, the admin student profile, the attention flags and Analytics matched. Gaps: learning time was reported from the real topic page (with the browser clock fast-forwarded, the server capped the second report at wall-clock time); the Overview, the student filter (mouse and keyboard, reload, phone), the profile's time and its link to Analytics, and the CSV column all checked. |
| 6B | Role-readiness ranking: transparent role frameworks, top 10 per role, AI summaries and reports, insufficient-data handling, admin overrides | Next (needs real student activity to be meaningful) |
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
