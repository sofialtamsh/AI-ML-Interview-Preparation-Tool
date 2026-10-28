/** Response shapes of the platform API (mirrors backend/app/schemas). */

export type Page<T> = { items: T[]; total: number; page: number; page_size: number }
export type Message = { message: string }

export type StudentStatus = 'active' | 'suspended' | 'deactivated'
export type AdminStatus = 'active' | 'disabled'

export type StudentMe = {
  id: string
  student_code: string
  full_name: string
  email: string
  status: StudentStatus
  cohort_name: string | null
  created_at: string
  last_login_at: string | null
}

export type StudentSession = {
  id: string
  created_at: string
  last_seen_at: string
  expires_at: string
  ip_address: string | null
  user_agent: string | null
  current: boolean
}

export type RoleSummary = { id: string; key: string; name: string }

export type AdminMe = {
  id: string
  email: string
  full_name: string
  must_change_password: boolean
  roles: RoleSummary[]
  permissions: string[]
}

export type AdminUser = {
  id: string
  email: string
  full_name: string
  status: AdminStatus
  must_change_password: boolean
  roles: RoleSummary[]
  last_login_at: string | null
  created_at: string
}

export type Role = {
  id: string
  key: string
  name: string
  description: string
  is_system: boolean
  permissions: string[]
  admin_count: number
}

export type PermissionInfo = { key: string; description: string }

export type Cohort = { id: string; name: string; description: string }
export type CohortWithCount = Cohort & { student_count: number }

export type StudentListItem = {
  id: string
  student_code: string
  full_name: string
  email: string
  status: StudentStatus
  cohort: Cohort | null
  created_at: string
  last_login_at: string | null
}

export type LoginEvent = {
  created_at: string
  success: boolean
  failure_reason: string | null
  ip_address: string | null
  user_agent: string | null
}

export type StudentDetail = StudentListItem & {
  locked_until: string | null
  active_sessions: number
  recent_logins: LoginEvent[]
}

export type DailyCount = { day: string; count: number }

export type StudentStats = {
  total: number
  by_status: Partial<Record<StudentStatus, number>>
  active_last_7_days: number
  new_last_7_days: number
  new_last_30_days: number
  registrations_last_30_days: DailyCount[]
  recent: StudentListItem[]
}

export type Overview = { students: StudentStats | null; active_admins: number | null }

export type AuditLogEntry = {
  id: number
  action: string
  entity_type: string
  entity_id: string | null
  details: Record<string, unknown>
  actor_name: string | null
  actor_email: string | null
  ip_address: string | null
  created_at: string
}

// Money values arrive as decimal strings (exact), e.g. "0.00042".
export type UsageTotals = {
  calls: number
  input_tokens: number
  output_tokens: number
  cost_usd: string
}

export type UsageWeek = UsageTotals & { start: string; end: string }

export type UsageSlice = { key: string; calls: number; cost_usd: string }

export type AiUsageReport = {
  currency: 'USD'
  tracking_start: string
  timezone: string
  weeks: UsageWeek[]
  selected: { start: string; end: string; by_feature: UsageSlice[]; by_model: UsageSlice[] } | null
  all_time: UsageTotals
}

export type SpendCap = {
  limit_usd: string
  remaining_usd: string | null
  reset_interval: string | null
  resets_at: string | null
}

export type AiProviderStatus = {
  provider: 'openrouter'
  configured: boolean
  ok: boolean
  error: string | null
  key_usage_usd: string | null
  cap: SpendCap | null
  is_free_tier: boolean | null
}

// --- Interview data sources ---------------------------------------------------------------------

export type ConnectorType = 'web_pages' | 'json_api' | 'rss_feed' | 'file_upload'
export type AuthMethod =
  | 'none'
  | 'http_basic'
  | 'bearer_token'
  | 'api_key_header'
  | 'api_key_query'
  | 'form_login'
export type ConnectionStatus = 'untested' | 'ok' | 'failed' | 'manual_import_required'
export type JobStatus =
  | 'queued'
  | 'running'
  | 'succeeded'
  | 'completed_with_errors'
  | 'failed'
  | 'cancelled'

/** A settings input described by the backend; its validation lives there too. */
export type FieldSpec = {
  key: string
  label: string
  kind: 'text' | 'password' | 'url' | 'number' | 'textarea' | 'lines' | 'select' | 'checkbox'
  help: string
  placeholder: string
  options: { value: string; label: string }[] | null
  required: boolean
  default: unknown
  min: number | null
  max: number | null
  /** Shown only when another field has one of these values ("*" = any non-empty value). */
  visible_when: Record<string, string[]> | null
}

export type ConnectorInfo = {
  key: ConnectorType
  label: string
  description: string
  uses_url: boolean
  auth_methods: AuthMethod[]
  settings_fields: FieldSpec[]
}

export type AuthMethodInfo = {
  key: AuthMethod
  label: string
  description: string
  settings_fields: FieldSpec[]
  secret_fields: FieldSpec[]
}

export type SourceCatalog = {
  connectors: ConnectorInfo[]
  auth_methods: AuthMethodInfo[]
  credential_storage_ready: boolean
  upload_extensions: string[]
  max_upload_mb: number
}

/** Which secrets are stored, never their values. */
export type CredentialStatus = {
  required: string[]
  stored: string[]
  complete: boolean
  updated_at: string | null
  updated_by: string | null
}

export type RunCounts = {
  seen?: number
  new?: number
  updated?: number
  unchanged?: number
  skipped_known?: number
}

export type JobKind =
  | 'source_fetch'
  | 'source_import'
  | 'exploration'
  | 'market_research'
  | 'content_generation'
  | 'content_narration'

export type JobSummary = {
  id: string
  kind: JobKind
  status: JobStatus
  source_id: string | null
  created_at: string
  started_at: string | null
  finished_at: string | null
  progress_done: number
  progress_total: number | null
  result: RunCounts & Record<string, number | string | undefined>
  error: string | null
  cancel_requested: boolean
  triggered_by: string | null
  file_name: string | null
}

export type JobDetail = JobSummary & {
  events: { level: 'info' | 'warning' | 'error'; message: string; created_at: string }[]
}

export type SourceListItem = {
  id: string
  name: string
  description: string
  connector_type: ConnectorType
  base_url: string | null
  auth_method: AuthMethod
  enabled: boolean
  removed_at: string | null
  connection_status: ConnectionStatus
  connection_message: string | null
  last_tested_at: string | null
  last_attempted_sync_at: string | null
  last_successful_sync_at: string | null
  record_count: number
  credentials: CredentialStatus
  active_job: JobSummary | null
  created_at: string
}

export type SourceDetail = SourceListItem & {
  config: Record<string, unknown>
  auth_config: Record<string, unknown>
}

export type FetchResult = {
  started: JobSummary[]
  skipped: { source_id: string; name: string | null; reason: string }[]
}

export type SourceRecord = {
  id: number
  external_id: string
  revision: number
  url: string | null
  title: string | null
  content_type: string
  content_length: number
  published_at: string | null
  fetched_at: string
  job_id: string
}

export type SourceRecordDetail = SourceRecord & { content: string; meta: Record<string, unknown> }

// --- Agents, intelligence and research ---------------------------------------------------------

export type AgentStatus = {
  ai_configured: boolean
  extraction_model: string
  research_model: string
  search_engine: string
  max_records_per_run: number
  max_cost_per_run_usd: string
  role_presets: string[]
}

export type AgentJob = JobSummary & {
  source_name: string | null
  cost_usd: string
  report_id: string | null
}

export type AgentJobDetail = AgentJob & {
  payload: Record<string, unknown>
  events: JobDetail['events']
}

export type StartResult = {
  started: AgentJob[]
  skipped: { source_id: string; name: string | null; reason: string }[]
}

export type ExplorationSource = {
  id: string
  name: string
  connector_type: ConnectorType
  enabled: boolean
  fetchable: boolean
  record_count: number
  unexplored: number
  questions: number
  pending_review: number
  last_explored_at: string | null
  active_job: JobSummary | null
}

export type ReviewStatus = 'pending_review' | 'approved' | 'rejected'
export type Difficulty = 'easy' | 'medium' | 'hard'
export type Trend = 'emerging' | 'rising' | 'stable' | 'declining' | 'unclear'

export type TopicRef = { id: string; slug: string; name: string; domain_name: string }
export type DomainWithTopics = { id: string; slug: string; name: string; topics: TopicRef[] }

export type ExperienceRef = {
  id: string
  company: string | null
  role: string | null
  interview_date: string | null
  period: string | null
  location: string | null
}

export type InterviewQuestion = {
  id: string
  original_text: string
  status: ReviewStatus
  grounded: boolean
  question_type: string
  difficulty: Difficulty | null
  round: string | null
  topic: TopicRef | null
  suggested_topic: string | null
  technologies: string[]
  duplicate_of_id: string | null
  experience: ExperienceRef
  source: { id: string; name: string }
  record: { id: number; title: string | null; url: string | null }
  created_at: string
  reviewed_by: string | null
  reviewed_at: string | null
  review_note: string | null
  seen_in_records: number
}

export type InterviewQuestionDetail = InterviewQuestion & {
  context: string
  duplicates: { id: string; original_text: string; status: ReviewStatus; company: string | null }[]
  duplicate_of_text: string | null
}

export type TopicSignal = 'asked_and_rising' | 'rising_in_market' | 'asked' | 'declining' | 'no_evidence'

export type TopicInsight = {
  topic: TopicRef
  approved_questions: number
  interview_records: number
  pending_questions: number
  roles: string[]
  research: { latest_trend: Trend | null; findings: number; reports: number; last_seen: string | null }
  signal: TopicSignal
}

export type IntelligenceSummary = {
  pending_questions: number
  approved_questions: number
  rejected_questions: number
  interview_records: number
  topics_with_evidence: number
  pending_recommendations: number
  pending_research_questions: number
  reports: number
  last_exploration_at: string | null
  last_research_at: string | null
}

export type ResearchScope = {
  roles: string[]
  focus: string
  region: string
  months: number
  sources_per_search: number
  max_cost_usd: string
}

export type ReportSummary = {
  id: string
  job_id: string
  title: string
  scope: ResearchScope
  model: string
  created_at: string
  triggered_by: string | null
  sources: number
  findings: number
  pending_recommendations: number
  questions: number
}

export type Recommendation = {
  id: string
  report_id: string
  report_title: string
  kind: 'add_topic' | 'prioritize' | 'deprioritize' | 'update_content'
  topic: TopicRef | null
  domain: { id: string; name: string } | null
  proposed_name: string | null
  rationale: string
  finding_ids: number[]
  status: 'pending' | 'approved' | 'rejected' | 'deferred'
  decided_by: string | null
  decided_at: string | null
  decision_note: string | null
  created_topic_id: string | null
  created_at: string
}

export type ResearchQuestion = {
  id: string
  text: string
  topic: TopicRef | null
  topic_label: string
  role: string | null
  rationale: string
  finding_ids: number[]
  status: ReviewStatus
}

export type ReportDetail = ReportSummary & {
  summary: string
  source_list: { id: number; url: string; title: string; site: string; excerpt: string; accessed_at: string }[]
  finding_list: {
    id: number
    topic: TopicRef | null
    topic_label: string
    roles: string[]
    skills: string[]
    observation: string
    trend: Trend
    evidence: { source_id: number; quote: string | null; quote_verified: boolean }[]
  }[]
  recommendations: Recommendation[]
  question_list: ResearchQuestion[]
}

// --- Learning content (mirrors backend/app/content/schemas.py) --------------------------------

export type Figure =
  | 'labels_vs_no_labels'
  | 'train_test_split'
  | 'decision_boundary'
  | 'overfit_underfit'
  | 'clusters'
  | 'scatter_line'
  | 'residuals'
  | 'neuron'
  | 'network'
  | 'activation_curves'
  | 'loss_bowl'
  | 'learning_rate'

export type Widget =
  | 'knn_classifier'
  | 'kmeans'
  | 'linear_regression'
  | 'neural_network'
  | 'activation_functions'
  | 'gradient_descent'

export type LessonCard = {
  kind: 'hook' | 'tldr' | 'intuition' | 'analogy' | 'steps' | 'math' | 'example' | 'myth' | 'interview' | 'recap'
  title: string
  body: string
  emoji: string | null
  bullets: string[]
  figure: Figure | null
  formula: string | null
  symbols: { symbol: string; meaning: string }[]
  myth: string | null
  fact: string | null
}

export type Lesson = {
  tagline: string
  minutes: number
  level: 'beginner' | 'intermediate' | 'advanced'
  cards: LessonCard[]
  key_terms: { term: string; meaning: string }[]
}

export type PlaygroundContent = {
  widget: Widget
  title: string
  intro: string
  tasks: { prompt: string; hint: string; insight: string }[]
}

export type PythonLabContent = {
  packages: string[]
  dataset: string
  steps: { title: string; explanation: string; code: string }[]
  expected_output: string
  mistakes: string[]
  applications: string[]
}

export type QuizContent = {
  questions: {
    difficulty: 'easy' | 'medium' | 'hard'
    kind: string
    prompt: string
    code: string | null
    options: string[]
    answer: number
    explanation: string
  }[]
}

export type RevisionContent = {
  definitions: { term: string; meaning: string }[]
  formulas: { name: string; expression: string; meaning: string }[]
  comparison: { title: string; columns: string[]; rows: string[][] } | null
  mistakes: string[]
  confusions: { pair: string; difference: string }[]
  takeaways: string[]
}

export type Scene = {
  title: string
  narration: string
  on_screen: string
  figure: Figure | null
  seconds: number
  audio_id?: string | null
}

export type VideoContent = { title: string; scenes: Scene[] }

export type InterviewEntry = {
  level: 'basic' | 'intermediate' | 'advanced'
  kind: string
  question: string
  answer: string
  interviewer_wants: string
  follow_ups: { question: string; answer: string }[]
  label: 'Practice question' | 'Asked in real interviews' | 'In demand right now'
  asked_for_role: string | null
}

export type InterviewContent = { questions: InterviewEntry[]; takeaways: string[] }

export type LearnTopicCard = {
  slug: string
  name: string
  tagline: string
  minutes: number
  level: string
  sections: string[]
}

export type LearnDomain = { slug: string; name: string; topics: LearnTopicCard[] }

export type LearnTopic = {
  slug: string
  name: string
  domain: { slug: string; name: string }
  tagline: string
  minutes: number
  level: string
  lesson: Lesson
  playground: PlaygroundContent | null
  video: VideoContent | null
  python: PythonLabContent | null
  interview: InterviewContent | null
  quiz: QuizContent | null
  revision: RevisionContent | null
}

// --- Content studio (admin) -------------------------------------------------------------------

export type ContentComponent = 'lesson' | 'playground' | 'video' | 'python' | 'interview' | 'quiz' | 'revision'
export type VersionStatus = 'draft' | 'under_review' | 'approved' | 'published' | 'archived' | 'rejected'
export type VersionOrigin = 'starter' | 'ai_generated' | 'edited'
export type TransitionAction = 'submit' | 'send_back' | 'reject' | 'approve' | 'publish' | 'unpublish' | 'archive'

export type VersionSummary = {
  id: string
  number: number
  status: VersionStatus
  origin: VersionOrigin
  model: string | null
  note: string | null
  created_at: string
  created_by: string | null
  reviewed_by: string | null
  reviewed_at: string | null
  review_note: string | null
  published_at: string | null
  job_id: string | null
  based_on_id: string | null
}

export type ContentTopicRef = { id: string; slug: string; name: string; domain_name: string; is_pilot: boolean }

export type ComponentState = {
  component: ContentComponent
  item_id: string | null
  published_number: number | null
  latest: VersionSummary | null
  versions: VersionSummary[]
}

export type TopicContent = {
  topic: ContentTopicRef
  may_generate: boolean
  has_playground: boolean
  components: ComponentState[]
}

export type TopicContentSummary = {
  topic: ContentTopicRef
  statuses: Partial<Record<ContentComponent, VersionStatus | null>>
  live: ContentComponent[]
  published: number
  may_generate: boolean
}

export type ContentOverview = {
  expansion_approved: boolean
  ai_configured: boolean
  content_model: string
  narration_model: string
  narration_voices: string[]
  topics: TopicContentSummary[]
}

export type CodeCheck = {
  id: number
  passed: boolean
  output: string
  error: string | null
  runtime: string
  duration_ms: number
  created_at: string
  current: boolean
}

export type NarrationClip = { id: string; position: number; size: number; voice: string | null }

export type VersionDetail = VersionSummary & {
  component: ContentComponent
  topic: ContentTopicRef
  body: Record<string, unknown>
  published: boolean
  code_checks: CodeCheck[]
  narration: NarrationClip[]
}

export type ContentJob = AgentJob & { topic: ContentTopicRef | null }
export type ContentJobDetail = ContentJob & { payload: Record<string, unknown>; events: JobDetail['events'] }

export type GenerateResult = {
  batch_id: string
  started: ContentJob[]
  skipped: { topic_id: string; name: string | null; reason: string }[]
}

export type BulkResult = { changed: string[]; skipped: Record<string, string> }

export type TaxonomyTopic = {
  id: string
  slug: string
  name: string
  description: string
  parent_id: string | null
  is_pilot: boolean
  archived: boolean
  published_components: number
}

export type TaxonomyDomain = {
  id: string
  slug: string
  name: string
  description: string
  archived: boolean
  topics: TaxonomyTopic[]
}
