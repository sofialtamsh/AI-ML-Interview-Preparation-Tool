import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { fireEvent, render, screen, waitFor, within } from '@testing-library/react'
import { createMemoryRouter, RouterProvider } from 'react-router'
import { afterEach, describe, expect, it, vi } from 'vitest'

import { ToastProvider } from '../../../components/ui/Toast'
import { adminKeys } from '../../../lib/queryClient'
import type { AdminMe, IntelligenceSummary, InterviewQuestion } from '../../../lib/types'
import IntelligencePage from './IntelligencePage'

// Synthetic fixtures for the UI only.
const ME: AdminMe = {
  id: 'a1',
  email: 'ops@example.com',
  full_name: 'Ops',
  must_change_password: false,
  roles: [],
  permissions: ['intelligence.view', 'intelligence.review'],
}

const SUMMARY: IntelligenceSummary = {
  pending_questions: 3,
  approved_questions: 0,
  rejected_questions: 0,
  interview_records: 0,
  topics_with_evidence: 0,
  pending_recommendations: 1,
  pending_research_questions: 0,
  reports: 1,
  last_exploration_at: null,
  last_research_at: null,
}

const question = (id: string, experience: string, text: string, extra: Partial<InterviewQuestion> = {}): InterviewQuestion => ({
  id,
  original_text: text,
  status: 'pending_review',
  grounded: true,
  question_type: 'conceptual',
  difficulty: null,
  round: null,
  topic: null,
  suggested_topic: null,
  technologies: [],
  duplicate_of_id: null,
  experience: {
    id: experience,
    company: experience === 'e1' ? 'Acme Analytics' : null,
    role: experience === 'e1' ? 'ML Engineer' : 'Data Scientist',
    interview_date: null,
    period: null,
    location: null,
  },
  source: { id: 's1', name: 'Alumni notes' },
  record: { id: 1, title: 'Fixture', url: null },
  created_at: '2026-10-27T08:00:00Z',
  reviewed_by: null,
  reviewed_at: null,
  review_note: null,
  seen_in_records: 0,
  ...extra,
})

const PENDING = [
  question('q1', 'e1', 'What is the bias-variance tradeoff?', {
    topic: { id: 't1', slug: 'machine-learning/model-evaluation', name: 'Model Evaluation', domain_name: 'Machine Learning' },
  }),
  question('q2', 'e1', 'How do you handle class imbalance?', { grounded: false }),
  question('q3', 'e2', 'Explain window functions in SQL.'),
]

function serve(routes: Record<string, unknown>) {
  const fetch = vi.fn(async (url: string, init?: RequestInit) => {
    const path = url.replace(/^\/api/, '').split('?')[0]
    const body = routes[`${init?.method ?? 'GET'} ${path}`]
    return new Response(JSON.stringify(body ?? {}), { status: body === undefined ? 404 : 200 })
  })
  vi.stubGlobal('fetch', fetch)
  return fetch
}

function renderPage() {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  client.setQueryData(adminKeys.me, ME)
  const router = createMemoryRouter([{ path: '*', element: <IntelligencePage /> }])
  render(
    <QueryClientProvider client={client}>
      <ToastProvider>
        <RouterProvider router={router} />
      </ToastProvider>
    </QueryClientProvider>,
  )
}

afterEach(() => vi.unstubAllGlobals())

describe('Interview intelligence review queue', () => {
  it('groups waiting questions by interview and flags paraphrases', async () => {
    serve({
      'GET /admin/intelligence/summary': SUMMARY,
      'GET /admin/intelligence/questions': { items: PENDING, total: 3, page: 1, page_size: 40 },
    })
    renderPage()
    const acme = (await screen.findByText('· Acme Analytics')).closest('section') as HTMLElement
    expect(within(acme).getByText('What is the bias-variance tradeoff?')).toBeInTheDocument()
    expect(within(acme).getByText('Model Evaluation')).toBeInTheDocument()
    expect(within(acme).getByText('Not word-for-word')).toBeInTheDocument()
    expect(screen.getByText('· Company not stated')).toBeInTheDocument()
    expect(screen.getByText(/1 curriculum recommendation/)).toBeInTheDocument()
  })

  it('approves every question from one interview at once', async () => {
    const fetch = serve({
      'GET /admin/intelligence/summary': SUMMARY,
      'GET /admin/intelligence/questions': { items: PENDING, total: 3, page: 1, page_size: 40 },
      'POST /admin/intelligence/questions/review': { updated: 2 },
    })
    renderPage()
    const acme = (await screen.findByText('· Acme Analytics')).closest('section') as HTMLElement
    fireEvent.click(within(acme).getByRole('button', { name: 'Approve all' }))
    await waitFor(() =>
      expect(fetch).toHaveBeenCalledWith('/api/admin/intelligence/questions/review', expect.anything()),
    )
    const [, init] = fetch.mock.calls.find(([url]) => url === '/api/admin/intelligence/questions/review')!
    expect(JSON.parse(init!.body as string)).toEqual({ question_ids: ['q1', 'q2'], status: 'approved' })
  })
})
