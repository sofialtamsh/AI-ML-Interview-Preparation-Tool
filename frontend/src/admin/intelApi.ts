/** Data hooks for the agents, interview intelligence and market research. */

import { keepPreviousData, useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useEffect, useRef } from 'react'

import { api } from '../lib/api'
import { adminKeys } from '../lib/queryClient'
import type {
  AgentJob,
  AgentJobDetail,
  AgentStatus,
  Difficulty,
  DomainWithTopics,
  ExperienceRef,
  ExplorationSource,
  IntelligenceSummary,
  InterviewQuestion,
  InterviewQuestionDetail,
  JobKind,
  JobStatus,
  Page,
  Recommendation,
  ReportDetail,
  ReportSummary,
  ResearchQuestion,
  ReviewStatus,
  StartResult,
  TopicInsight,
} from '../lib/types'

const LIVE_POLL_MS = 2500
const isLive = (status: JobStatus) => status === 'queued' || status === 'running'

export function useAgentStatus() {
  return useQuery({
    queryKey: adminKeys.agentStatus,
    queryFn: () => api<AgentStatus>('/admin/agents/status'),
    staleTime: 60_000,
  })
}

export function useTaxonomy() {
  return useQuery({
    queryKey: adminKeys.taxonomy,
    queryFn: () => api<DomainWithTopics[]>('/admin/intelligence/taxonomy'),
    staleTime: 5 * 60_000,
  })
}

/** Every change to agent work refreshes the views that summarise it. */
function useInvalidateAgents() {
  const queryClient = useQueryClient()
  return () => {
    for (const key of [
      adminKeys.agentJobs,
      adminKeys.explorationSources,
      adminKeys.intelligence,
      adminKeys.research,
      adminKeys.taxonomy,
      adminKeys.audit,
    ]) {
      queryClient.invalidateQueries({ queryKey: key })
    }
  }
}

// --- Runs ----------------------------------------------------------------------------------------

export type JobFilters = { kind: JobKind | ''; status: JobStatus | ''; page: number; pageSize?: number }

export function useAgentJobs(filters: JobFilters) {
  const params = new URLSearchParams({
    page: String(filters.page),
    page_size: String(filters.pageSize ?? 15),
  })
  if (filters.kind) params.set('kind', filters.kind)
  if (filters.status) params.set('status', filters.status)
  return useQuery({
    queryKey: [...adminKeys.agentJobs, 'list', params.toString()],
    queryFn: () => api<Page<AgentJob>>(`/admin/agents/jobs?${params}`),
    placeholderData: keepPreviousData,
    refetchInterval: (query) =>
      query.state.data?.items.some((job) => isLive(job.status)) ? LIVE_POLL_MS : false,
  })
}

/** Recent runs of one kind; when one of them finishes, the views it feeds are refreshed. */
export function useRecentRuns(kind: JobKind, pageSize = 5) {
  const runs = useAgentJobs({ kind, status: '', page: 1, pageSize })
  const refresh = useInvalidateAgents()
  const live = (runs.data?.items ?? [])
    .filter((job) => isLive(job.status))
    .map((job) => job.id)
    .join(',')
  const previous = useRef(live)
  useEffect(() => {
    if (previous.current && previous.current !== live) refresh()
    previous.current = live
  }, [live, refresh])
  return runs
}

export function useAgentJob(id: string, enabled = true) {
  return useQuery({
    queryKey: [...adminKeys.agentJobs, 'detail', id],
    queryFn: () => api<AgentJobDetail>(`/admin/agents/jobs/${id}`),
    enabled,
    refetchInterval: (query) =>
      query.state.data && isLive(query.state.data.status) ? LIVE_POLL_MS : false,
  })
}

export function useStopAgentJob() {
  const refresh = useInvalidateAgents()
  return useMutation({
    mutationFn: (id: string) => api<AgentJob>(`/admin/agents/jobs/${id}/cancel`, { method: 'POST' }),
    onSuccess: refresh,
  })
}

export function useRetryAgentJob() {
  const refresh = useInvalidateAgents()
  return useMutation({
    mutationFn: (id: string) => api<AgentJob>(`/admin/agents/jobs/${id}/retry`, { method: 'POST' }),
    onSuccess: refresh,
  })
}

// --- Exploration ----------------------------------------------------------------------------------

export function useExplorationSources() {
  return useQuery({
    queryKey: adminKeys.explorationSources,
    queryFn: () => api<ExplorationSource[]>('/admin/agents/exploration/sources'),
    refetchInterval: (query) => (query.state.data?.some((s) => s.active_job) ? LIVE_POLL_MS : false),
  })
}

export type ExplorationInput = {
  source_ids: string[]
  fetch_first: boolean
  max_records: number
  max_cost_usd: string
}

export function useStartExploration() {
  const refresh = useInvalidateAgents()
  return useMutation({
    mutationFn: (body: ExplorationInput) =>
      api<StartResult>('/admin/agents/exploration', { method: 'POST', body }),
    onSuccess: refresh,
  })
}

// --- Intelligence --------------------------------------------------------------------------------

export function useIntelligenceSummary() {
  return useQuery({
    queryKey: [...adminKeys.intelligence, 'summary'],
    queryFn: () => api<IntelligenceSummary>('/admin/intelligence/summary'),
  })
}

export type QuestionFilters = {
  status: ReviewStatus | ''
  topicId: string
  sourceId: string
  q: string
  hideDuplicates: boolean
  notGrounded: boolean
  page: number
  pageSize: number
}

export function useQuestions(filters: QuestionFilters) {
  const params = new URLSearchParams({ page: String(filters.page), page_size: String(filters.pageSize) })
  if (filters.status) params.set('status', filters.status)
  if (filters.topicId) params.set('topic_id', filters.topicId)
  if (filters.sourceId) params.set('source_id', filters.sourceId)
  if (filters.q.trim()) params.set('q', filters.q.trim())
  if (filters.hideDuplicates) params.set('hide_duplicates', 'true')
  if (filters.notGrounded) params.set('not_grounded', 'true')
  return useQuery({
    queryKey: [...adminKeys.intelligence, 'questions', params.toString()],
    queryFn: ({ signal }) =>
      api<Page<InterviewQuestion>>(`/admin/intelligence/questions?${params}`, { signal }),
    placeholderData: keepPreviousData,
  })
}

export function useQuestion(id: string) {
  return useQuery({
    queryKey: [...adminKeys.intelligence, 'question', id],
    queryFn: () => api<InterviewQuestionDetail>(`/admin/intelligence/questions/${id}`),
  })
}

export type QuestionReviewInput = {
  status?: ReviewStatus
  topic_id?: string | null
  difficulty?: Difficulty | null
  round?: string | null
  duplicate_of_id?: string | null
  review_note?: string | null
}

export function useReviewQuestion() {
  const refresh = useInvalidateAgents()
  return useMutation({
    mutationFn: ({ id, ...body }: QuestionReviewInput & { id: string }) =>
      api<InterviewQuestionDetail>(`/admin/intelligence/questions/${id}`, { method: 'PATCH', body }),
    onSuccess: refresh,
  })
}

export function useBulkReview() {
  const refresh = useInvalidateAgents()
  return useMutation({
    mutationFn: (body: { question_ids: string[]; status: 'approved' | 'rejected' }) =>
      api<{ updated: number }>('/admin/intelligence/questions/review', { method: 'POST', body }),
    onSuccess: refresh,
  })
}

export function useCorrectInterview() {
  const refresh = useInvalidateAgents()
  return useMutation({
    mutationFn: ({ id, ...body }: Partial<Omit<ExperienceRef, 'id'>> & { id: string }) =>
      api<ExperienceRef>(`/admin/intelligence/experiences/${id}`, { method: 'PATCH', body }),
    onSuccess: refresh,
  })
}

export function useTopicInsights() {
  return useQuery({
    queryKey: [...adminKeys.intelligence, 'topics'],
    queryFn: () => api<TopicInsight[]>('/admin/intelligence/topics'),
  })
}

// --- Research ----------------------------------------------------------------------------------

export type ResearchInput = {
  roles: string[]
  focus: string
  region: string
  months: number
  sources_per_search: number
  max_cost_usd: string
}

export function useStartResearch() {
  const refresh = useInvalidateAgents()
  return useMutation({
    mutationFn: (body: ResearchInput) => api<AgentJob>('/admin/agents/research', { method: 'POST', body }),
    onSuccess: refresh,
  })
}

export function useReports(page: number) {
  return useQuery({
    queryKey: [...adminKeys.research, 'reports', page],
    queryFn: () => api<Page<ReportSummary>>(`/admin/research/reports?page=${page}&page_size=10`),
    placeholderData: keepPreviousData,
  })
}

export function useReport(id: string) {
  return useQuery({
    queryKey: [...adminKeys.research, 'report', id],
    queryFn: () => api<ReportDetail>(`/admin/research/reports/${id}`),
  })
}

export function useRecommendations() {
  return useQuery({
    queryKey: [...adminKeys.research, 'recommendations', 'pending'],
    queryFn: () => api<Recommendation[]>('/admin/research/recommendations?status=pending'),
  })
}

export function useDecideRecommendation() {
  const refresh = useInvalidateAgents()
  return useMutation({
    mutationFn: ({ id, ...body }: { id: string; decision: 'approved' | 'rejected' | 'deferred'; note: string }) =>
      api<Recommendation>(`/admin/research/recommendations/${id}/decision`, { method: 'POST', body }),
    onSuccess: refresh,
  })
}

export function useReviewResearchQuestion() {
  const refresh = useInvalidateAgents()
  return useMutation({
    mutationFn: ({ id, status }: { id: string; status: ReviewStatus }) =>
      api<ResearchQuestion>(`/admin/research/questions/${id}`, { method: 'PATCH', body: { status } }),
    onSuccess: refresh,
  })
}
