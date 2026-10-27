import { keepPreviousData, useMutation, useQuery, useQueryClient } from '@tanstack/react-query'

import { api, ApiError } from '../lib/api'
import { adminKeys } from '../lib/queryClient'
import type {
  AdminMe,
  AdminStatus,
  AdminUser,
  AiProviderStatus,
  AiUsageReport,
  AuditLogEntry,
  CohortWithCount,
  Overview,
  Page,
  PermissionInfo,
  Role,
  StudentDetail,
  StudentListItem,
  StudentStatus,
} from '../lib/types'

// --- Session ------------------------------------------------------------------------------

export function useAdminMe() {
  return useQuery({
    queryKey: adminKeys.me,
    queryFn: async () => {
      try {
        return await api<AdminMe>('/admin/auth/me')
      } catch (error) {
        if (error instanceof ApiError && error.status === 401) return null
        throw error
      }
    },
    staleTime: 5 * 60_000,
  })
}

/** The signed-in admin; only call inside <RequireAdmin>. */
export function useCurrentAdmin(): AdminMe {
  const { data } = useAdminMe()
  if (!data) throw new Error('useCurrentAdmin used outside <RequireAdmin>')
  return data
}

/** UI convenience only; the backend enforces every permission independently. */
export function useCan(...anyOf: string[]): boolean {
  const { data } = useAdminMe()
  return !!data && anyOf.some((p) => data.permissions.includes(p))
}

export function useAdminLogin() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (body: { email: string; password: string }) =>
      api<AdminMe>('/admin/auth/login', { method: 'POST', body }),
    onSuccess: (me) => queryClient.setQueryData(adminKeys.me, me),
  })
}

export function useAdminLogout() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: () => api<void>('/admin/auth/logout', { method: 'POST' }),
    onSettled: () => {
      queryClient.removeQueries({ queryKey: ['admin'] })
      queryClient.setQueryData(adminKeys.me, null)
    },
  })
}

export function useAdminChangePassword() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (body: { current_password: string; new_password: string }) =>
      api<AdminMe>('/admin/auth/change-password', { method: 'POST', body }),
    onSuccess: (me) => queryClient.setQueryData(adminKeys.me, me),
  })
}

// --- Overview & students -------------------------------------------------------------------

export function useOverview() {
  return useQuery({ queryKey: adminKeys.overview, queryFn: () => api<Overview>('/admin/overview') })
}

export type StudentFilters = {
  q: string
  status: StudentStatus | ''
  cohort_id: string
  page: number
}

export function useStudents(filters: StudentFilters, pageSize = 20) {
  const params = new URLSearchParams({ page: String(filters.page), page_size: String(pageSize) })
  if (filters.q.trim()) params.set('q', filters.q.trim())
  if (filters.status) params.set('status', filters.status)
  if (filters.cohort_id) params.set('cohort_id', filters.cohort_id)
  return useQuery({
    queryKey: [...adminKeys.students, 'list', params.toString()],
    queryFn: ({ signal }) => api<Page<StudentListItem>>(`/admin/students?${params}`, { signal }),
    placeholderData: keepPreviousData,
  })
}

export function useStudent(id: string) {
  return useQuery({
    queryKey: adminKeys.student(id),
    queryFn: () => api<StudentDetail>(`/admin/students/${id}`),
  })
}

export function useUpdateStudent(id: string) {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (body: { status?: StudentStatus; cohort_id?: string | null }) =>
      api<StudentDetail>(`/admin/students/${id}`, { method: 'PATCH', body }),
    onSuccess: (student) => {
      queryClient.setQueryData(adminKeys.student(id), student)
      queryClient.invalidateQueries({ queryKey: [...adminKeys.students, 'list'] })
      queryClient.invalidateQueries({ queryKey: adminKeys.overview })
      queryClient.invalidateQueries({ queryKey: adminKeys.cohorts })
    },
  })
}

export function useCohorts(enabled = true) {
  return useQuery({
    queryKey: adminKeys.cohorts,
    queryFn: () => api<CohortWithCount[]>('/admin/cohorts'),
    enabled,
  })
}

export function useCreateCohort() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (body: { name: string; description: string }) =>
      api<CohortWithCount>('/admin/cohorts', { method: 'POST', body }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: adminKeys.cohorts }),
  })
}

// --- Admin team & roles --------------------------------------------------------------------

export function useAdminUsers() {
  return useQuery({ queryKey: adminKeys.adminUsers, queryFn: () => api<AdminUser[]>('/admin/admin-users') })
}

export type AdminUserInput = {
  email?: string
  full_name?: string
  status?: AdminStatus
  role_ids?: string[]
  temporary_password?: string
}

export function useSaveAdminUser() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: ({ id, ...body }: AdminUserInput & { id?: string }) =>
      id
        ? api<AdminUser>(`/admin/admin-users/${id}`, { method: 'PATCH', body })
        : api<AdminUser>('/admin/admin-users', { method: 'POST', body }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: adminKeys.adminUsers })
      queryClient.invalidateQueries({ queryKey: adminKeys.roles })
    },
  })
}

export function useRoles(enabled = true) {
  return useQuery({ queryKey: adminKeys.roles, queryFn: () => api<Role[]>('/admin/roles'), enabled })
}

export function usePermissions() {
  return useQuery({
    queryKey: adminKeys.permissions,
    queryFn: () => api<PermissionInfo[]>('/admin/permissions'),
    staleTime: Infinity,
  })
}

export type RoleInput = { name: string; description: string; permissions: string[] }

export function useSaveRole() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: ({ id, ...body }: RoleInput & { id?: string }) =>
      id
        ? api<Role>(`/admin/roles/${id}`, { method: 'PATCH', body })
        : api<Role>('/admin/roles', { method: 'POST', body }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: adminKeys.roles }),
  })
}

export function useDeleteRole() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (id: string) => api<void>(`/admin/roles/${id}`, { method: 'DELETE' }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: adminKeys.roles }),
  })
}

// --- Audit -----------------------------------------------------------------------------------

export function useAuditLogs(page: number, action: string) {
  const params = new URLSearchParams({ page: String(page), page_size: '25' })
  if (action) params.set('action', action)
  return useQuery({
    queryKey: [...adminKeys.audit, params.toString()],
    queryFn: () => api<Page<AuditLogEntry>>(`/admin/audit-logs?${params}`),
    placeholderData: keepPreviousData,
  })
}

// --- AI usage --------------------------------------------------------------------------------

/** Weekly AI spend; `week` is a week's start date, or null for the current week. */
export function useAiUsage(week: string | null) {
  return useQuery({
    queryKey: [...adminKeys.aiUsage, week ?? 'current'],
    queryFn: () => api<AiUsageReport>(`/admin/ai-usage${week ? `?week=${week}` : ''}`),
    placeholderData: keepPreviousData,
  })
}

export function useAiProviderStatus() {
  return useQuery({
    queryKey: adminKeys.aiProvider,
    queryFn: () => api<AiProviderStatus>('/admin/ai-usage/provider'),
    staleTime: 60_000,
  })
}
