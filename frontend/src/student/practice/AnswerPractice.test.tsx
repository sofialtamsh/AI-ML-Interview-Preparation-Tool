import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, describe, expect, it, vi } from 'vitest'

import type { AttemptDetail, InterviewEntry, PracticeStatus } from '../../lib/types'
import { DELIVERY, FEEDBACK } from '../../test/fixtures/practice'
import { AnswerPractice } from './AnswerPractice'

const ITEM: InterviewEntry = {
  level: 'basic',
  kind: 'conceptual',
  question: 'What is supervised learning?',
  answer: 'Learning from labelled examples.',
  interviewer_wants: 'Labels, mapping, an example.',
  follow_ups: [],
  label: 'Practice question',
  asked_for_role: null,
}

const STATUS: PracticeStatus = { feedback_available: true, reason: null, daily_limit: 10, used_today: 3, max_seconds: 180 }

const attempt = (id: string, overrides: Partial<AttemptDetail> = {}): AttemptDetail => ({
  id,
  topic_slug: 'ml/supervised',
  question_index: 0,
  question: ITEM.question,
  status: 'completed',
  score: 7.1,
  verdict: 'Almost there',
  duration_ms: 102_000,
  created_at: new Date().toISOString(),
  transcript: 'we learn from labelled examples',
  delivery: DELIVERY,
  feedback: FEEDBACK,
  error: null,
  ...overrides,
})

function serve(status: PracticeStatus, attempts: AttemptDetail[]) {
  const fetch = vi.fn(async (url: string, init?: RequestInit) => {
    if (init?.method === 'DELETE') return new Response(null, { status: 204 })
    if (url.endsWith('/practice/status')) return Response.json(status)
    if (url.includes('/practice/attempts?')) return Response.json(attempts)
    const found = attempts.find((a) => url.endsWith(`/practice/attempts/${a.id}`))
    return found ? Response.json(found) : Response.json({ detail: 'Not found' }, { status: 404 })
  })
  vi.stubGlobal('fetch', fetch)
  return fetch
}

function renderPractice({ answered = false, onTake = () => {} }: { answered?: boolean; onTake?: () => void } = {}) {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  render(
    <QueryClientProvider client={client}>
      <AnswerPractice
        topic="ml/supervised"
        versionId="v1"
        index={0}
        item={ITEM}
        strongAnswer={<p>The strong answer</p>}
        answered={answered}
        onTake={onTake}
      />
    </QueryClientProvider>,
  )
}

afterEach(() => vi.unstubAllGlobals())

describe('answer practice', () => {
  it("shows today's feedback quota and earlier tries, and opens a try's feedback", async () => {
    serve(STATUS, [attempt('a1'), attempt('a2', { status: 'no_answer', score: null, verdict: null, feedback: null, transcript: 'Um hi' })])
    renderPractice()
    expect(await screen.findByText('AI feedback: 7 of 10 left today')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Record my answer' })).toBeInTheDocument()

    await userEvent.click(await screen.findByRole('button', { name: /7\.1 out of 10, Almost there/ }))
    expect(await screen.findByText('You nailed the core idea.')).toBeInTheDocument()

    await userEvent.click(screen.getByRole('button', { name: /No answer heard/ }))
    expect(await screen.findByText(/barely hear an answer/)).toBeInTheDocument()
    expect(screen.getByText(/Um hi/)).toBeInTheDocument()
  })

  it('says why feedback is unavailable, while recording still works', async () => {
    serve({ ...STATUS, feedback_available: false, reason: "AI feedback isn't set up yet." }, [])
    renderPractice()
    expect(await screen.findByText("AI feedback isn't set up yet.")).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Record my answer' })).toBeEnabled()
  })

  it('shows progress while scoring and the reason when it failed', async () => {
    serve(STATUS, [
      attempt('busy', { status: 'processing', score: null, verdict: null, feedback: null, transcript: 'heard it' }),
      attempt('bad', { status: 'failed', score: null, verdict: null, feedback: null, error: 'The AI is busy right now. Try again in a minute.' }),
    ])
    renderPractice()
    await userEvent.click(await screen.findByRole('button', { name: /Scoring/ }))
    expect(await screen.findByText(/Thinking like an interviewer/)).toBeInTheDocument()
    await userEvent.click(screen.getByRole('button', { name: /Didn't work/ }))
    expect(await screen.findByText('The AI is busy right now. Try again in a minute.')).toBeInTheDocument()
  })

  it('keeps the strong answer locked until the first take', async () => {
    serve(STATUS, [])
    renderPractice()
    expect(await screen.findByText(/unlock after your first take/)).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: /show the strong answer/i })).not.toBeInTheDocument()
    expect(screen.queryByText('The strong answer')).not.toBeInTheDocument()
  })

  it('unlocks the strong answer once there is a take', async () => {
    serve(STATUS, [attempt('a1')])
    renderPractice()
    await userEvent.click(await screen.findByRole('button', { name: 'Show the strong answer' }))
    expect(screen.getByText('The strong answer')).toBeInTheDocument()
  })

  it('unlocks for a take saved to the account earlier, on any device', async () => {
    serve(STATUS, [])
    renderPractice({ answered: true })
    expect(await screen.findByRole('button', { name: 'Show the strong answer' })).toBeInTheDocument()
  })

  it('lets students who cannot record see the answer anyway', async () => {
    vi.stubGlobal('MediaRecorder', undefined)
    serve(STATUS, [])
    renderPractice()
    await userEvent.click(await screen.findByRole('button', { name: 'Record my answer' }))
    await userEvent.click(screen.getByRole('button', { name: 'Turn on camera' }))
    await userEvent.click(await screen.findByRole('button', { name: /can't record right now/i }))
    expect(screen.getByText('The strong answer')).toBeInTheDocument()
  })

  it('deletes a try after confirming', async () => {
    const fetch = serve(STATUS, [attempt('a1')])
    renderPractice()
    await userEvent.click(await screen.findByRole('button', { name: /7\.1 out of 10, Almost there/ }))
    await userEvent.click(await screen.findByRole('button', { name: 'Delete this try' }))
    await userEvent.click(screen.getByRole('button', { name: 'Delete' }))
    await vi.waitFor(() =>
      expect(fetch).toHaveBeenCalledWith('/api/student/practice/attempts/a1', expect.objectContaining({ method: 'DELETE' })),
    )
  })
})
