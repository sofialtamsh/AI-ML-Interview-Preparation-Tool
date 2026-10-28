/** Data hooks for the content studio and the topic taxonomy. */

import { keepPreviousData, useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useEffect, useRef } from 'react'

import { api } from '../lib/api'
import { adminKeys } from '../lib/queryClient'
import type {
  BulkResult,
  CodeCheck,
  ContentComponent,
  ContentJob,
  ContentJobDetail,
  ContentOverview,
  GenerateResult,
  JobStatus,
  Page,
  TaxonomyDomain,
  TopicContent,
  TransitionAction,
  VersionDetail,
} from '../lib/types'

const LIVE_POLL_MS = 2500
const isLive = (status: JobStatus) => status === 'queued' || status === 'running'

export const adminMediaUrl = (id: string) => `/api/admin/content/media/${id}`

/** Any content change can touch the overview, a topic's state, versions and runs. */
function useRefreshContent() {
  const queryClient = useQueryClient()
  return () => {
    queryClient.invalidateQueries({ queryKey: adminKeys.content })
    queryClient.invalidateQueries({ queryKey: adminKeys.audit })
  }
}

export function useContentOverview() {
  return useQuery({ queryKey: adminKeys.content, queryFn: () => api<ContentOverview>('/admin/content') })
}

export function useTopicContent(topicId: string) {
  return useQuery({
    queryKey: adminKeys.contentTopic(topicId),
    queryFn: () => api<TopicContent>(`/admin/content/topics/${topicId}`),
  })
}

export function useVersion(versionId: string | null) {
  return useQuery({
    queryKey: adminKeys.contentVersion(versionId ?? ''),
    queryFn: () => api<VersionDetail>(`/admin/content/versions/${versionId}`),
    enabled: !!versionId,
  })
}

/** Recent generation and narration runs; when one finishes, the content views refresh. */
export function useContentJobs(topicId?: string, pageSize = 6) {
  const params = new URLSearchParams({ page: '1', page_size: String(pageSize) })
  if (topicId) params.set('topic_id', topicId)
  const runs = useQuery({
    queryKey: [...adminKeys.contentJobs, params.toString()],
    queryFn: () => api<Page<ContentJob>>(`/admin/content/jobs?${params}`),
    placeholderData: keepPreviousData,
    refetchInterval: (query) => (query.state.data?.items.some((job) => isLive(job.status)) ? LIVE_POLL_MS : false),
  })
  const refresh = useRefreshContent()
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

export function useContentJob(id: string, enabled = true) {
  return useQuery({
    queryKey: [...adminKeys.contentJobs, 'detail', id],
    queryFn: () => api<ContentJobDetail>(`/admin/content/jobs/${id}`),
    enabled,
    refetchInterval: (query) => (query.state.data && isLive(query.state.data.status) ? LIVE_POLL_MS : false),
  })
}

export function useStopContentJob() {
  const refresh = useRefreshContent()
  return useMutation({
    mutationFn: (id: string) => api<ContentJob>(`/admin/content/jobs/${id}/cancel`, { method: 'POST' }),
    onSuccess: refresh,
  })
}

export type GenerateInput = {
  topic_ids: string[]
  components: ContentComponent[]
  use_intelligence: boolean
  max_cost_usd: string
}

export function useGenerate() {
  const refresh = useRefreshContent()
  return useMutation({
    mutationFn: (body: GenerateInput) => api<GenerateResult>('/admin/content/generate', { method: 'POST', body }),
    onSuccess: refresh,
  })
}

export function useSaveVersion(topicId: string, component: ContentComponent) {
  const refresh = useRefreshContent()
  return useMutation({
    mutationFn: (body: { body: unknown; based_on_id: string | null; note: string }) =>
      api<VersionDetail>(`/admin/content/topics/${topicId}/components/${component}/versions`, { method: 'POST', body }),
    onSuccess: refresh,
  })
}

export function useTransition() {
  const refresh = useRefreshContent()
  return useMutation({
    mutationFn: ({ versionId, action, note }: { versionId: string; action: TransitionAction; note?: string }) =>
      api<VersionDetail>(`/admin/content/versions/${versionId}/transition`, {
        method: 'POST',
        body: { action, note: note || null },
      }),
    onSuccess: refresh,
  })
}

export function useBulkTransition(topicId: string) {
  const refresh = useRefreshContent()
  return useMutation({
    mutationFn: (action: 'submit' | 'approve' | 'publish') =>
      api<BulkResult>(`/admin/content/topics/${topicId}/bulk`, { method: 'POST', body: { action } }),
    onSuccess: refresh,
  })
}

export function useRestoreVersion() {
  const refresh = useRefreshContent()
  return useMutation({
    mutationFn: (versionId: string) => api<VersionDetail>(`/admin/content/versions/${versionId}/restore`, { method: 'POST' }),
    onSuccess: refresh,
  })
}

export function useRecordCodeCheck() {
  const refresh = useRefreshContent()
  return useMutation({
    mutationFn: ({ versionId, ...body }: { versionId: string; output: string; error: string | null; duration_ms: number; runtime: string }) =>
      api<CodeCheck>(`/admin/content/versions/${versionId}/code-checks`, { method: 'POST', body }),
    onSuccess: refresh,
  })
}

export function useNarrate() {
  const refresh = useRefreshContent()
  return useMutation({
    mutationFn: ({ versionId, voice }: { versionId: string; voice: string }) =>
      api<ContentJob>(`/admin/content/versions/${versionId}/narration`, { method: 'POST', body: { voice } }),
    onSuccess: refresh,
  })
}

export function useSetExpansion() {
  const refresh = useRefreshContent()
  return useMutation({
    mutationFn: (approved: boolean) => api<{ approved: boolean }>('/admin/content/expansion', { method: 'PUT', body: { approved } }),
    onSuccess: refresh,
  })
}

// --- Taxonomy --------------------------------------------------------------------------------

export function useTaxonomyAdmin() {
  return useQuery({ queryKey: adminKeys.taxonomyAdmin, queryFn: () => api<TaxonomyDomain[]>('/admin/taxonomy') })
}

/** Every taxonomy write returns the full tree; other views that list topics refresh too. */
function useTaxonomyWrite<T>(request: (input: T) => Promise<TaxonomyDomain[]>) {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: request,
    onSuccess: (domains) => {
      queryClient.setQueryData(adminKeys.taxonomyAdmin, domains)
      for (const key of [adminKeys.taxonomy, adminKeys.content, adminKeys.intelligence, adminKeys.research, adminKeys.audit]) {
        queryClient.invalidateQueries({ queryKey: key })
      }
    },
  })
}

export const useCreateDomain = () =>
  useTaxonomyWrite((body: { name: string; description: string }) =>
    api<TaxonomyDomain[]>('/admin/taxonomy/domains', { method: 'POST', body }),
  )

export const useUpdateDomain = () =>
  useTaxonomyWrite(({ id, ...body }: { id: string; name?: string; description?: string; archived?: boolean }) =>
    api<TaxonomyDomain[]>(`/admin/taxonomy/domains/${id}`, { method: 'PATCH', body }),
  )

export const useCreateTopic = () =>
  useTaxonomyWrite((body: { domain_id: string; name: string; description: string }) =>
    api<TaxonomyDomain[]>('/admin/taxonomy/topics', { method: 'POST', body }),
  )

export const useUpdateTopic = () =>
  useTaxonomyWrite(
    ({ id, ...body }: { id: string; name?: string; description?: string; archived?: boolean; is_pilot?: boolean }) =>
      api<TaxonomyDomain[]>(`/admin/taxonomy/topics/${id}`, { method: 'PATCH', body }),
  )
