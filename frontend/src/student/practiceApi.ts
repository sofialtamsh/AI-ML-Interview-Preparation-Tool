import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'

import { api } from '../lib/api'
import { studentKeys } from '../lib/queryClient'
import type { AttemptDetail, AttemptSummary, PracticeStatus } from '../lib/types'

const ACTIVE = new Set(['queued', 'processing'])

export function usePracticeStatus() {
  return useQuery({ queryKey: studentKeys.practiceStatus, queryFn: () => api<PracticeStatus>('/student/practice/status') })
}

export function usePracticeAttempts(topic: string) {
  return useQuery({
    queryKey: studentKeys.practiceAttempts(topic),
    queryFn: () => api<AttemptSummary[]>(`/student/practice/attempts?topic=${encodeURIComponent(topic)}`),
  })
}

/** One attempt, polled while the AI is still working on it. */
export function usePracticeAttempt(id: string | null) {
  const queryClient = useQueryClient()
  return useQuery({
    queryKey: studentKeys.practiceAttempt(id ?? ''),
    queryFn: async () => {
      const attempt = await api<AttemptDetail>(`/student/practice/attempts/${id}`)
      if (!ACTIVE.has(attempt.status)) {
        queryClient.invalidateQueries({ queryKey: studentKeys.practiceAttempts(attempt.topic_slug) })
        queryClient.invalidateQueries({ queryKey: studentKeys.practiceStatus })
      }
      return attempt
    },
    enabled: id !== null,
    refetchInterval: (query) => (query.state.data && ACTIVE.has(query.state.data.status) ? 2000 : false),
  })
}

export function useSubmitAnswer() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (input: { topic: string; versionId: string; questionIndex: number; wav: Blob }) => {
      const form = new FormData()
      form.append('topic', input.topic)
      form.append('version_id', input.versionId)
      form.append('question_index', String(input.questionIndex))
      form.append('audio', input.wav, 'answer.wav')
      return api<AttemptDetail>('/student/practice/attempts', { method: 'POST', body: form })
    },
    onSuccess: (attempt) => {
      queryClient.setQueryData(studentKeys.practiceAttempt(attempt.id), attempt)
      queryClient.invalidateQueries({ queryKey: studentKeys.practiceAttempts(attempt.topic_slug) })
      queryClient.invalidateQueries({ queryKey: studentKeys.practiceStatus })
    },
  })
}

export function useDeleteAttempt() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (attempt: AttemptSummary) => api<void>(`/student/practice/attempts/${attempt.id}`, { method: 'DELETE' }),
    onSuccess: (_, attempt) => {
      queryClient.removeQueries({ queryKey: studentKeys.practiceAttempt(attempt.id) })
      queryClient.invalidateQueries({ queryKey: studentKeys.practiceAttempts(attempt.topic_slug) })
    },
  })
}
