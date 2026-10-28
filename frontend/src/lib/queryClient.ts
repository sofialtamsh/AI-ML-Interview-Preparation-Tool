import { QueryClient } from '@tanstack/react-query'

import { ApiError, setUnauthorizedHandler } from './api'

export const adminKeys = {
  me: ['admin', 'me'] as const,
  overview: ['admin', 'overview'] as const,
  students: ['admin', 'students'] as const,
  student: (id: string) => ['admin', 'students', id] as const,
  cohorts: ['admin', 'cohorts'] as const,
  adminUsers: ['admin', 'admin-users'] as const,
  roles: ['admin', 'roles'] as const,
  permissions: ['admin', 'permissions'] as const,
  audit: ['admin', 'audit'] as const,
  aiUsage: ['admin', 'ai-usage'] as const,
  aiProvider: ['admin', 'ai-provider'] as const,
  sourceCatalog: ['admin', 'source-catalog'] as const,
  sources: ['admin', 'sources'] as const,
  source: (id: string) => ['admin', 'sources', id] as const,
  sourceJobs: (id: string) => ['admin', 'sources', id, 'jobs'] as const,
  sourceRecords: (id: string) => ['admin', 'sources', id, 'records'] as const,
  agentStatus: ['admin', 'agent-status'] as const,
  agentJobs: ['admin', 'agent-jobs'] as const,
  explorationSources: ['admin', 'exploration-sources'] as const,
  intelligence: ['admin', 'intelligence'] as const,
  taxonomy: ['admin', 'taxonomy'] as const,
  research: ['admin', 'research'] as const,
  content: ['admin', 'content'] as const,
  contentTopic: (id: string) => ['admin', 'content', 'topic', id] as const,
  contentVersion: (id: string) => ['admin', 'content', 'version', id] as const,
  contentJobs: ['admin', 'content', 'jobs'] as const,
  taxonomyAdmin: ['admin', 'taxonomy-admin'] as const,
}

export const studentKeys = {
  me: ['student', 'me'] as const,
  sessions: ['student', 'sessions'] as const,
  learn: ['student', 'learn'] as const,
  topic: (slug: string) => ['student', 'learn', slug] as const,
}

export const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 30_000,
      refetchOnWindowFocus: false,
      retry: (count, error) =>
        !(error instanceof ApiError && error.status >= 400 && error.status < 500) && count < 2,
    },
  },
})

// A 401 on any authenticated call means the session ended: drop the cached identity so the
// route guard sends the user to the right sign-in page.
setUnauthorizedHandler((audience) => {
  const meKey = audience === 'admin' ? adminKeys.me : studentKeys.me
  queryClient.setQueryData(meKey, null)
  queryClient.removeQueries({
    predicate: (q) => q.queryKey[0] === audience && q.queryKey[1] !== 'me',
  })
})
