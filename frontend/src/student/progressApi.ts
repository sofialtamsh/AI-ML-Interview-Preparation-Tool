import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'

import { api } from '../lib/api'
import { studentKeys } from '../lib/queryClient'
import type { ContentComponent, ProgressKind, ProgressSummary, QuizResult, TopicProgress } from '../lib/types'

const topicPath = (slug: string) => slug.split('/').map(encodeURIComponent).join('/')

/** The student's own dashboard summary, from what's stored against their account. */
export function useMyProgress() {
  return useQuery({ queryKey: studentKeys.progress, queryFn: () => api<ProgressSummary>('/student/progress') })
}

export function useTopicProgress(slug: string) {
  return useQuery({
    queryKey: studentKeys.topicProgress(slug),
    queryFn: () => api<TopicProgress>(`/student/progress/topics/${topicPath(slug)}`),
    enabled: slug.length > 0,
  })
}

/** Saves one learning event; the topic's progress comes back and refreshes the page. */
export function useRecordProgress(slug: string) {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (body: { component: ContentComponent; kind: ProgressKind; data?: Record<string, unknown> }) =>
      api<TopicProgress>('/student/progress/events', { method: 'POST', body: { topic: slug, data: {}, ...body } }),
    onSuccess: (progress) => {
      queryClient.setQueryData(studentKeys.topicProgress(slug), progress)
      queryClient.invalidateQueries({ queryKey: studentKeys.progress, exact: true })
    },
  })
}

export function useSubmitQuiz(slug: string) {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (body: { version_id: string; answers: (number | null)[]; duration_seconds: number }) =>
      api<QuizResult>('/student/progress/quiz-attempts', { method: 'POST', body: { topic: slug, ...body } }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: studentKeys.topicProgress(slug) })
      queryClient.invalidateQueries({ queryKey: studentKeys.progress, exact: true })
    },
  })
}
