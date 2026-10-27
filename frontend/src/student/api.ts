import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'

import { api, ApiError } from '../lib/api'
import { studentKeys } from '../lib/queryClient'
import type { Message, StudentMe, StudentSession } from '../lib/types'

export function useStudentMe() {
  return useQuery({
    queryKey: studentKeys.me,
    queryFn: async () => {
      try {
        return await api<StudentMe>('/student/auth/me')
      } catch (error) {
        if (error instanceof ApiError && error.status === 401) return null
        throw error
      }
    },
    staleTime: 5 * 60_000,
  })
}

/** The signed-in student; only call inside <RequireStudent>. */
export function useCurrentStudent(): StudentMe {
  const { data } = useStudentMe()
  if (!data) throw new Error('useCurrentStudent used outside <RequireStudent>')
  return data
}

function useSetMe() {
  const queryClient = useQueryClient()
  return (me: StudentMe | null) => queryClient.setQueryData(studentKeys.me, me)
}

export function useStudentLogin() {
  const setMe = useSetMe()
  return useMutation({
    mutationFn: (body: { email: string; password: string }) =>
      api<StudentMe>('/student/auth/login', { method: 'POST', body }),
    onSuccess: setMe,
  })
}

export function useStudentRegister() {
  const setMe = useSetMe()
  return useMutation({
    mutationFn: (body: { full_name: string; email: string; password: string }) =>
      api<StudentMe>('/student/auth/register', { method: 'POST', body }),
    onSuccess: setMe,
  })
}

export function useStudentLogout() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: () => api<void>('/student/auth/logout', { method: 'POST' }),
    onSettled: () => {
      queryClient.removeQueries({ queryKey: ['student'] })
      queryClient.setQueryData(studentKeys.me, null)
    },
  })
}

export function useRequestPasswordReset() {
  return useMutation({
    mutationFn: (email: string) =>
      api<Message>('/student/auth/password-reset/request', { method: 'POST', body: { email } }),
  })
}

export function useConfirmPasswordReset() {
  return useMutation({
    mutationFn: (body: { token: string; new_password: string }) =>
      api<Message>('/student/auth/password-reset/confirm', { method: 'POST', body }),
  })
}

export function useUpdateProfile() {
  const setMe = useSetMe()
  return useMutation({
    mutationFn: (body: { full_name: string }) =>
      api<StudentMe>('/student/me', { method: 'PATCH', body }),
    onSuccess: setMe,
  })
}

export function useChangePassword() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (body: { current_password: string; new_password: string }) =>
      api<Message>('/student/me/password', { method: 'POST', body }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: studentKeys.sessions }),
  })
}

export function useSessions() {
  return useQuery({
    queryKey: studentKeys.sessions,
    queryFn: () => api<StudentSession[]>('/student/me/sessions'),
  })
}

export function useRevokeSession() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (session: StudentSession) =>
      api<void>(`/student/me/sessions/${session.id}`, { method: 'DELETE' }),
    onSuccess: (_, session) => {
      if (session.current) {
        // Signing out this device is a logout: forget the identity right away.
        queryClient.removeQueries({ queryKey: ['student'] })
        queryClient.setQueryData(studentKeys.me, null)
      } else {
        queryClient.invalidateQueries({ queryKey: studentKeys.sessions })
      }
    },
  })
}

export function useRevokeOtherSessions() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: () => api<Message>('/student/me/sessions/revoke-others', { method: 'POST' }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: studentKeys.sessions }),
  })
}
