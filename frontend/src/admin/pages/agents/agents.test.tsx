import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, screen } from '@testing-library/react'
import { createMemoryRouter, RouterProvider } from 'react-router'
import { afterEach, describe, expect, it, vi } from 'vitest'

import { ToastProvider } from '../../../components/ui/Toast'
import { adminKeys } from '../../../lib/queryClient'
import type { AdminMe, AgentJob, ReportDetail } from '../../../lib/types'
import ReportPage from './ReportPage'
import { resultCounts, runHeadline } from './shared'

const job = (overrides: Partial<AgentJob>): AgentJob => ({
  id: 'j1',
  kind: 'exploration',
  status: 'succeeded',
  source_id: 's1',
  created_at: '2026-10-27T08:00:00Z',
  started_at: '2026-10-27T08:00:01Z',
  finished_at: '2026-10-27T08:01:00Z',
  progress_done: 3,
  progress_total: 3,
  result: {},
  error: null,
  cancel_requested: false,
  triggered_by: 'Ops',
  file_name: null,
  source_name: 'Alumni notes',
  cost_usd: '0.0300',
  report_id: null,
  ...overrides,
})

describe('run summaries', () => {
  it('describe each kind of run in its own terms', () => {
    expect(runHeadline(job({ result: { questions: 4, interview_records: 2 } }))).toBe('4 questions from 2 interviews')
    expect(runHeadline(job({ status: 'running', progress_done: 1, progress_total: 5 }))).toBe('Reading 1 of 5 records')
    expect(runHeadline(job({ kind: 'market_research', result: { findings: 6, recommendations: 2 } }))).toBe(
      '6 cited findings, 2 recommendations',
    )
    expect(runHeadline(job({ status: 'failed', error: 'Key rejected' }))).toBe('Key rejected')
  })

  it('only list counters that happened, beyond the main three', () => {
    const counts = resultCounts(job({ result: { records_read: 3, interview_records: 2, questions: 4, failed: 1 } }))
    expect(counts.map((c) => c.label)).toEqual(['Records read', 'Interviews found', 'Questions extracted', "Couldn't read"])
  })
})

// A synthetic report (UI fixture only).
const REPORT: ReportDetail = {
  id: 'r1',
  job_id: 'j1',
  title: 'AI/ML hiring, fixture report',
  scope: { roles: ['ML Engineer'], focus: '', region: 'India', months: 6, sources_per_search: 5, max_cost_usd: '0.50' },
  model: 'google/gemini-3.8-flash',
  created_at: '2026-10-27T08:00:00Z',
  triggered_by: 'Ops',
  sources: 1,
  findings: 2,
  pending_recommendations: 0,
  questions: 1,
  summary: 'RAG demand is rising (fixture).',
  source_list: [{ id: 10, url: 'https://jobs.example.org/report', title: 'Hiring report', site: 'jobs.example.org', excerpt: 'RAG rose.', accessed_at: '2026-10-27T08:00:00Z' }],
  finding_list: [
    { id: 1, topic: null, topic_label: 'RAG', roles: [], skills: [], observation: 'RAG demand rose.', trend: 'rising', evidence: [{ source_id: 10, quote: 'RAG rose.', quote_verified: true }] },
    { id: 2, topic: null, topic_label: 'Agents', roles: [], skills: [], observation: 'Agents appear.', trend: 'emerging', evidence: [{ source_id: 10, quote: 'Agents everywhere', quote_verified: false }] },
  ],
  recommendations: [],
  question_list: [{ id: 'rq1', text: 'How would you evaluate a RAG pipeline?', topic: null, topic_label: 'RAG', role: null, rationale: 'Rising demand.', finding_ids: [1], status: 'pending_review' }],
}

afterEach(() => vi.unstubAllGlobals())

describe('research report', () => {
  it('shows which quotes were found in their sources and labels practice questions', async () => {
    vi.stubGlobal('fetch', vi.fn(async () => new Response(JSON.stringify(REPORT), { status: 200 })))
    const client = new QueryClient({ defaultOptions: { queries: { retry: false } } })
    const me: AdminMe = { id: 'a', email: 'a@example.com', full_name: 'A', must_change_password: false, roles: [], permissions: ['agents.view'] }
    client.setQueryData(adminKeys.me, me)
    const router = createMemoryRouter([{ path: '/r/:id', element: <ReportPage /> }], { initialEntries: ['/r/r1'] })
    render(
      <QueryClientProvider client={client}>
        <ToastProvider>
          <RouterProvider router={router} />
        </ToastProvider>
      </QueryClientProvider>,
    )
    expect(await screen.findByText('AI/ML hiring, fixture report')).toBeInTheDocument()
    expect(screen.getByLabelText('Quote found in the source')).toBeInTheDocument()
    expect(screen.getByLabelText('Quote not found in the search excerpt')).toBeInTheDocument()
    expect(screen.getByText(/These are not real interview questions/)).toBeInTheDocument()
    expect(screen.getAllByText('[1] jobs.example.org')).toHaveLength(2)
  })
})
