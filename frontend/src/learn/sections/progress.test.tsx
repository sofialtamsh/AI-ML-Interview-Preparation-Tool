import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it, vi } from 'vitest'

import type { Lesson, PlaygroundContent, QuizContent } from '../../lib/types'
import starter from '../../test/fixtures/starter-content.json'
import { LessonDeck } from './LessonDeck'
import { PlaygroundSection } from './PlaygroundSection'
import { QuizSection } from './QuizSection'

const topic = (starter as Record<string, Record<string, unknown>>)['machine-learning/supervised-learning']

const QUIZ: QuizContent = {
  questions: [
    { difficulty: 'easy', kind: 'concept', prompt: 'One?', code: null, options: ['A', 'B'], answer: 0, explanation: 'Because.' },
    { difficulty: 'easy', kind: 'concept', prompt: 'Two?', code: null, options: ['A', 'B'], answer: 1, explanation: 'Because.' },
  ],
}

async function finishQuiz() {
  await userEvent.click(screen.getByRole('button', { name: /A$/ }))
  await userEvent.click(screen.getByRole('button', { name: 'Next question' }))
  await userEvent.click(screen.getByRole('button', { name: /A$/ }))
  await userEvent.click(screen.getByRole('button', { name: 'See my score' }))
}

describe('progress reporting', () => {
  it('saves a finished quiz once and shows the attempt and best score', async () => {
    const onFinish = vi.fn().mockResolvedValue({ attempt_number: 2, correct: 1, total: 2, score_pct: 50, best_pct: 100 })
    render(<QuizSection quiz={QUIZ} onFinish={onFinish} />)
    await finishQuiz()
    expect(await screen.findByText(/Saved · attempt 2 · your best 100%/)).toBeInTheDocument()
    expect(onFinish).toHaveBeenCalledTimes(1)
    expect(onFinish.mock.calls[0][0]).toEqual([0, 0])
  })

  it('offers to save again when saving fails', async () => {
    const onFinish = vi.fn().mockRejectedValueOnce(new Error('offline')).mockResolvedValue({ attempt_number: 1, correct: 1, total: 2, score_pct: 50, best_pct: 50 })
    render(<QuizSection quiz={QUIZ} onFinish={onFinish} />)
    await finishQuiz()
    await userEvent.click(await screen.findByRole('button', { name: 'Save again' }))
    expect(await screen.findByText(/Saved · attempt 1/)).toBeInTheDocument()
    expect(onFinish).toHaveBeenCalledTimes(2)
  })

  it('works without saving in the admin preview', async () => {
    render(<QuizSection quiz={QUIZ} />)
    await finishQuiz()
    expect(screen.getByText('1 / 2')).toBeInTheDocument()
    expect(screen.queryByText(/Saved/)).not.toBeInTheDocument()
  })

  it('reports each new furthest lesson card, and all of them when shown at once', async () => {
    const lesson = topic.lesson as Lesson
    const onProgress = vi.fn()
    render(<LessonDeck lesson={lesson} onProgress={onProgress} />)
    expect(onProgress).toHaveBeenLastCalledWith('lesson_progress', { seen: 1, of: lesson.cards.length })
    await userEvent.click(screen.getByRole('button', { name: /next/i }))
    expect(onProgress).toHaveBeenLastCalledWith('lesson_progress', { seen: 2, of: lesson.cards.length })
    await userEvent.click(screen.getByRole('button', { name: /previous|back/i }))
    expect(onProgress).toHaveBeenCalledTimes(2) // going back reports nothing new
    await userEvent.click(screen.getByRole('button', { name: /show all cards/i }))
    expect(onProgress).toHaveBeenLastCalledWith('lesson_progress', { seen: lesson.cards.length, of: lesson.cards.length })
  })

  it('reports playground tasks as they are tried', async () => {
    const playground = topic.playground as PlaygroundContent
    const onProgress = vi.fn()
    render(<PlaygroundSection playground={playground} onProgress={onProgress} />)
    await userEvent.click(screen.getAllByRole('button', { name: /I tried it/ })[1])
    expect(onProgress).toHaveBeenCalledWith('playground_task', { task: 1, of: playground.tasks.length })
  })
})
