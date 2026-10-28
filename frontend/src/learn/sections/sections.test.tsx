// src/test/fixtures/starter-content.json is the backend's starter content in canonical form, exactly
// as the API serves it. Regenerate it after changing the starter content or the schemas:
//   cd backend && uv run python -m app.cli export-starter-fixture ../frontend/src/test/fixtures/starter-content.json
// Rendering every component of every pilot topic catches shape drift between backend and frontend.
import { render, screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it } from 'vitest'

import { studentView } from '../../admin/pages/content/shared'
import { diffLines } from '../../lib/diff'
import type { QuizContent } from '../../lib/types'
import starter from '../../test/fixtures/starter-content.json'
import { RichText } from '../RichText'
import { SECTION_ORDER, SectionBody } from '.'
import { LessonDeck } from './LessonDeck'
import { PlaygroundSection } from './PlaygroundSection'
import { QuizSection } from './QuizSection'

type Body = Record<string, unknown>
const TOPICS = Object.entries(starter as Record<string, Record<string, Body>>)

describe('every starter component renders', () => {
  for (const [slug, content] of TOPICS) {
    for (const component of SECTION_ORDER) {
      it(`${slug} · ${component}`, () => {
        const body = studentView(component, content[component], [])
        const { container } = render(<SectionBody component={component} body={body} />)
        expect(container.textContent?.length).toBeGreaterThan(50)
      })
    }
  }
})

describe('student-facing interview view', () => {
  it('never carries sources or origins, only the label', () => {
    const [, content] = TOPICS[0]
    const body = content.interview as { questions: Body[] }
    const tagged = { ...body, questions: body.questions.map((q, i) => (i === 0 ? { ...q, origin: 'actual_interview', source_ref: 'abc', asked_for_role: 'ML Engineer' } : q)) }
    const view = studentView('interview', tagged, []) as { questions: Body[] }
    expect(view.questions[0].label).toBe('Asked in real interviews')
    expect(view.questions[1].label).toBe('Practice question')
    expect(view.questions[1].asked_for_role).toBeNull()
  })
})

describe('lesson deck', () => {
  it('moves card by card and shows key terms at the end', async () => {
    const user = userEvent.setup()
    const lesson = TOPICS[0][1].lesson as never as Parameters<typeof LessonDeck>[0]['lesson']
    render(<LessonDeck lesson={lesson} />)
    expect(screen.getByText(`1 / ${lesson.cards.length}`)).toBeInTheDocument()
    await user.click(screen.getByRole('button', { name: /next/i }))
    expect(screen.getByText(`2 / ${lesson.cards.length}`)).toBeInTheDocument()
    await user.click(screen.getByRole('button', { name: new RegExp(`Card ${lesson.cards.length}:`) }))
    expect(screen.getByText('Key terms')).toBeInTheDocument()
  })
})

describe('quiz', () => {
  const quiz: QuizContent = {
    questions: [
      { difficulty: 'easy', kind: 'concept', prompt: 'Pick B', code: null, options: ['A', 'B'], answer: 1, explanation: 'B is right.' },
      { difficulty: 'hard', kind: 'math', prompt: 'Pick A', code: null, options: ['A', 'B'], answer: 0, explanation: 'A is right.' },
    ],
  }

  it('gives instant feedback, scores, reviews misses and retries', async () => {
    const user = userEvent.setup()
    render(<QuizSection quiz={quiz} />)
    await user.click(screen.getByRole('button', { name: /B$/ }))
    expect(screen.getByText(/Nailed it/)).toBeInTheDocument()
    await user.click(screen.getByRole('button', { name: 'Next question' }))
    await user.click(screen.getByRole('button', { name: /B$/ }))
    expect(screen.getByText('Not quite.')).toBeInTheDocument()
    await user.click(screen.getByRole('button', { name: 'See my score' }))
    expect(screen.getByText('1 / 2')).toBeInTheDocument()
    const review = screen.getByText('Review your misses').closest('section')!
    expect(within(review).getByText('Pick A')).toBeInTheDocument()
    await user.click(screen.getByRole('button', { name: 'Try again' }))
    expect(screen.getByText('Pick B')).toBeInTheDocument()
  })
})

describe('playground tasks', () => {
  it('reveal the hint and then the insight', async () => {
    const user = userEvent.setup()
    const playground = TOPICS.find(([slug]) => slug.endsWith('regression'))![1].playground as never as Parameters<typeof PlaygroundSection>[0]['playground']
    render(<PlaygroundSection playground={playground} />)
    const first = playground.tasks[0]
    await user.click(screen.getAllByRole('button', { name: 'Need a hint?' })[0])
    expect(screen.getByText(first.hint)).toBeInTheDocument()
    await user.click(screen.getAllByRole('button', { name: /show the insight/ })[0])
    expect(screen.getByText(first.insight)).toBeInTheDocument()
    expect(screen.getByText(`1 / ${playground.tasks.length} done`)).toBeInTheDocument()
  })
})

describe('rich text', () => {
  it('renders bold and code but never HTML', () => {
    const { container } = render(<RichText text={'**Big** `x = 1` <img src=x onerror=alert(1)>'} />)
    expect(container.querySelector('strong')?.textContent).toBe('Big')
    expect(container.querySelector('code')?.textContent).toBe('x = 1')
    expect(container.querySelector('img')).toBeNull()
    expect(container.textContent).toContain('<img src=x onerror=alert(1)>')
  })
})

describe('line diff', () => {
  it('marks added and removed lines', () => {
    expect(diffLines('a\nb\nc', 'a\nc\nd')).toEqual([
      { kind: 'same', text: 'a' },
      { kind: 'removed', text: 'b' },
      { kind: 'same', text: 'c' },
      { kind: 'added', text: 'd' },
    ])
  })
})
