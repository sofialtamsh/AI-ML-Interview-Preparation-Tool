import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import type { ReactNode } from 'react'
import { MemoryRouter } from 'react-router'
import { afterEach, describe, expect, it, vi } from 'vitest'

import { ToastProvider } from '../../../components/ui/Toast'
import type { PilotEvaluation, VersionDetail, VersionQuality } from '../../../lib/types'
import { PilotEvaluationCard, pilotSummary } from './PilotEvaluation'
import { QualityPanel } from './QualityPanel'

const VERSION = {
  id: 'v1',
  number: 2,
  component: 'quiz',
  body: { questions: [{ options: ['Mean', 'Median', 'Mode'] }, { options: ['A', 'B', 'C'] }] },
} as unknown as VersionDetail

const QUALITY: VersionQuality = {
  automated: {
    errors: 1,
    warnings: 1,
    checks: [
      { key: 'companies', label: 'No company names', status: 'error', note: 'Compared with 3 company name(s).', findings: [{ severity: 'error', message: 'Mentions the company “Acme”.', where: 'questions 1 · prompt' }] },
      { key: 'answer_key', label: 'Answer key looks balanced', status: 'warning', note: null, findings: [{ severity: 'warning', message: '6 of 7 answers are option B.', where: null }] },
      { key: 'links', label: 'No links', status: 'passed', note: null, findings: [] },
    ],
  },
  ai_reviews: [
    {
      id: 'r1',
      created_at: '2026-10-28T10:00:00Z',
      model: 'google/gemini-3.8-flash',
      summary: 'Mostly accurate; one wrong key.',
      scores: { factual_correctness: 4, math_consistency: null, assessment_quality: 3 },
      average: 3.5,
      issues: [{ severity: 'error', location: 'Question 1', quote: 'Which is robust to outliers?', problem: 'Two answers fit.', fix: 'Reword.' }],
      quiz_check: [
        { question: 1, key: 0, picked: 1, confident: true, agrees: false },
        { question: 2, key: 2, picked: 2, confident: true, agrees: true },
      ],
      dropped_issues: 1,
      requested_by: 'Platform Admin',
    },
  ],
  ratings: {
    criteria: [
      { key: 'technical_correctness', label: 'Technical correctness' },
      { key: 'clarity', label: 'Educational clarity' },
    ],
    ratings: [{ admin: 'Riya', mine: false, scores: { technical_correctness: 5, clarity: 4 }, average: 4.5, note: 'Nice.', created_at: '2026-10-28T09:00:00Z' }],
    average: 4.5,
  },
  review_model: 'google/gemini-3.8-flash',
  ai_configured: true,
}

const EVALUATION: PilotEvaluation = {
  expansion_approved: false,
  topics: [
    {
      topic: { id: 't1', slug: 'ml/supervised', name: 'Supervised Learning', domain_name: 'ML', is_pilot: true },
      components: [
        { component: 'lesson', latest_number: 2, latest_status: 'published', published_number: 2, errors: 0, warnings: 0, ai_score: 4.2, rating: 4.5, ratings: 2 },
        { component: 'quiz', latest_number: 1, latest_status: 'under_review', published_number: null, errors: 1, warnings: 0, ai_score: null, rating: null, ratings: 0 },
      ],
    },
  ],
  totals: { components: 2, published: 1, with_errors: 1, ai_reviewed: 1, rated: 1, average_rating: 4.5, average_ai_score: 4.2 },
}

function serve(permissions: string[]) {
  const fetch = vi.fn(async (url: string, init?: RequestInit) => {
    if (url.endsWith('/auth/me')) return Response.json({ id: 'a', email: 'a@x.com', full_name: 'A', permissions })
    if (url.endsWith('/quality')) return Response.json(QUALITY)
    if (url.endsWith('/ratings') && init?.method === 'POST') return Response.json(QUALITY.ratings, { status: 201 })
    if (url.endsWith('/pilot-evaluation')) return Response.json(EVALUATION)
    return Response.json({ detail: 'Not found' }, { status: 404 })
  })
  vi.stubGlobal('fetch', fetch)
  return fetch
}

function wrap(children: ReactNode) {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return render(
    <QueryClientProvider client={client}>
      <ToastProvider>
        <MemoryRouter>{children}</MemoryRouter>
      </ToastProvider>
    </QueryClientProvider>,
  )
}

afterEach(() => vi.unstubAllGlobals())

describe('quality panel', () => {
  it('shows automated checks, the AI review with its answer-key check, and ratings', async () => {
    serve(['content.review'])
    wrap(<QualityPanel version={VERSION} />)
    expect(await screen.findByText('1 error(s)')).toBeInTheDocument()
    expect(screen.getByText('Mentions the company “Acme”.')).toBeInTheDocument()
    expect(screen.getByText('questions 1 · prompt')).toBeInTheDocument()

    expect(screen.getByText(/disagreed on 1/)).toBeInTheDocument()
    expect(screen.getByText(/Question 1: the key says/)).toHaveTextContent('the key says A (Mean), the reviewer picked B (Median)')
    expect(screen.getByText('Not applicable')).toBeInTheDocument() // maths score is null
    expect(screen.getByText(/1 issue\(s\) were dropped/)).toBeInTheDocument()
    expect(screen.getByText(/advice, not verification/)).toBeInTheDocument()

    expect(screen.getByText('Average 4.5 / 5 from 1')).toBeInTheDocument()
    expect(screen.getByText('Riya')).toBeInTheDocument()
  })

  it('saves a rating once every criterion is scored', async () => {
    const fetch = serve(['content.review'])
    wrap(<QualityPanel version={VERSION} />)
    const save = await screen.findByRole('button', { name: 'Save my rating' })
    expect(save).toBeDisabled()
    const correctness = screen.getByRole('group', { name: 'Technical correctness' })
    await userEvent.click(within(correctness).getByLabelText('4'))
    await userEvent.click(within(screen.getByRole('group', { name: 'Educational clarity' })).getByLabelText('5'))
    await userEvent.click(save)
    await vi.waitFor(() =>
      expect(fetch).toHaveBeenCalledWith(
        '/api/admin/content/versions/v1/ratings',
        expect.objectContaining({ method: 'POST', body: JSON.stringify({ scores: { technical_correctness: 4, clarity: 5 } }) }),
      ),
    )
  })

  it('hides the AI review and rating actions from admins who can only generate', async () => {
    serve(['content.generate'])
    wrap(<QualityPanel version={VERSION} />)
    await screen.findByText('1 error(s)')
    expect(screen.queryByRole('button', { name: /review again|run ai review/i })).not.toBeInTheDocument()
    expect(screen.queryByRole('button', { name: /save my rating/i })).not.toBeInTheDocument()
  })
})

describe('pilot evaluation', () => {
  it('summarises the pilot for the expansion decision', async () => {
    expect(pilotSummary(EVALUATION)).toBe(
      '1 of 2 components published · 1 with check errors · 1 AI-reviewed (avg 4.2/5) · 1 rated by reviewers (avg 4.5/5)',
    )
    serve(['content.review'])
    wrap(<PilotEvaluationCard />)
    expect(await screen.findByText('1 / 2')).toBeInTheDocument()
    expect(screen.queryByRole('table')).not.toBeInTheDocument() // details are folded away
    await userEvent.click(screen.getByRole('button', { name: /show topic details/i }))
    expect(screen.getByRole('link', { name: 'Lesson cards: Published' })).toHaveAttribute('href', '/admin/content/t1?c=lesson')
    expect(screen.getByRole('link', { name: 'Quiz: In review, 1 check errors' })).toBeInTheDocument()
  })
})
