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
