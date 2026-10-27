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

export type JobSummary = {
  id: string
  kind: 'source_fetch' | 'source_import'
  status: JobStatus
  source_id: string | null
  created_at: string
  started_at: string | null
  finished_at: string | null
  progress_done: number
  result: RunCounts
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
