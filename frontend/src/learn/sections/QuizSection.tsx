import { CircleCheck, CircleX, RotateCcw } from 'lucide-react'
import { useState } from 'react'

import { Button } from '../../components/ui/Button'
import { Badge } from '../../components/ui/Feedback'
import { cn } from '../../lib/cn'
import type { QuizContent } from '../../lib/types'
import { PythonCode } from '../PythonCode'
import { RichText } from '../RichText'

const DIFFICULTY_TONE = { easy: 'success', medium: 'warning', hard: 'danger' } as const

function verdict(score: number, total: number) {
  const ratio = score / total
  if (ratio === 1) return { emoji: '🏆', line: 'Flawless. You own this topic.' }
  if (ratio >= 0.75) return { emoji: '🔥', line: 'Strong! Review the misses and you are interview-ready.' }
  if (ratio >= 0.5) return { emoji: '💪', line: 'Getting there. Revisit the cards for the ones you missed.' }
  return { emoji: '🌱', line: 'Good start. Replay the lesson and the playground, then try again.' }
}

export function QuizSection({ quiz }: { quiz: QuizContent }) {
  const [index, setIndex] = useState(0)
  const [answers, setAnswers] = useState<(number | null)[]>(() => quiz.questions.map(() => null))
  const total = quiz.questions.length
  const finished = index >= total
  const score = answers.filter((a, i) => a === quiz.questions[i].answer).length

  if (finished) {
    const { emoji, line } = verdict(score, total)
    const missed = quiz.questions.map((q, i) => ({ q, i })).filter(({ q, i }) => answers[i] !== q.answer)
    return (
      <div className="mx-auto max-w-2xl space-y-4">
        <div className="animate-pop rounded-3xl bg-gradient-to-br from-brand-600 to-fuchsia-600 p-8 text-center text-white">
          <p className="text-6xl" aria-hidden>
            {emoji}
          </p>
          <p className="mt-3 font-display text-4xl font-bold tabular-nums">
            {score} / {total}
          </p>
          <p className="mt-2 text-white/90">{line}</p>
          <Button
            variant="secondary"
            className="mt-5"
            icon={<RotateCcw className="size-4" />}
            onClick={() => {
              setAnswers(quiz.questions.map(() => null))
              setIndex(0)
            }}
          >
            Try again
          </Button>
        </div>
        {missed.length > 0 && (
          <section className="rounded-3xl bg-white p-5 ring-1 ring-slate-200">
            <h3 className="font-display text-lg font-bold text-slate-900">Review your misses</h3>
            <ul className="mt-3 space-y-3">
              {missed.map(({ q, i }) => (
                <li key={i} className="rounded-2xl bg-slate-50 p-4">
                  <p className="font-medium text-slate-900">
                    <RichText text={q.prompt} />
                  </p>
                  <p className="mt-1 text-sm text-emerald-700">
                    ✓ <RichText text={q.options[q.answer]} />
                  </p>
                  <p className="mt-1 text-sm text-slate-600">
                    <RichText text={q.explanation} />
                  </p>
                </li>
              ))}
            </ul>
          </section>
        )}
      </div>
    )
  }

  const question = quiz.questions[index]
  const chosen = answers[index]
  const answered = chosen !== null

  return (
    <div className="mx-auto max-w-2xl space-y-4">
      <div className="flex items-center gap-3">
        <div className="h-2 flex-1 overflow-hidden rounded-full bg-slate-200" role="progressbar" aria-valuemin={0} aria-valuemax={total} aria-valuenow={index}>
          <div className="h-full rounded-full bg-gradient-to-r from-brand-500 to-fuchsia-500 transition-all" style={{ width: `${(index / total) * 100}%` }} />
        </div>
        <span className="text-sm font-semibold text-slate-600 tabular-nums">
          {index + 1}/{total}
        </span>
      </div>

      <div key={index} className="animate-fade-up space-y-4 rounded-3xl bg-white p-5 ring-1 ring-slate-200 sm:p-6">
        <div className="flex flex-wrap gap-1.5">
          <Badge tone={DIFFICULTY_TONE[question.difficulty]} className="capitalize">
            {question.difficulty}
          </Badge>
          <Badge className="capitalize">{question.kind}</Badge>
        </div>
        <p className="font-display text-xl font-bold text-slate-900">
          <RichText text={question.prompt} />
        </p>
        {question.code && <PythonCode code={question.code} />}
        <div className="grid gap-2" role="group" aria-label="Options">
          {question.options.map((option, i) => {
            const right = i === question.answer
            const picked = i === chosen
            return (
              <button
                key={i}
                type="button"
                disabled={answered}
                onClick={() => setAnswers(answers.map((a, j) => (j === index ? i : a)))}
                className={cn(
                  'flex items-center gap-3 rounded-2xl px-4 py-3 text-left ring-1 transition',
                  !answered && 'bg-white ring-slate-200 hover:bg-brand-50 hover:ring-brand-300',
                  answered && right && 'bg-emerald-50 ring-2 ring-emerald-500',
                  answered && picked && !right && 'bg-rose-50 ring-2 ring-rose-500',
                  answered && !right && !picked && 'bg-white opacity-60 ring-slate-200',
                )}
              >
                <span className="grid size-7 shrink-0 place-items-center rounded-full bg-slate-100 text-sm font-bold text-slate-600">
                  {answered && right ? <CircleCheck className="size-5 text-emerald-600" aria-label="Correct answer" /> : answered && picked ? <CircleX className="size-5 text-rose-600" aria-label="Your answer" /> : String.fromCharCode(65 + i)}
                </span>
                <span className="text-slate-800">
                  <RichText text={option} />
                </span>
              </button>
            )
          })}
        </div>
        {answered && (
          <div className={cn('animate-pop rounded-2xl px-4 py-3', chosen === question.answer ? 'bg-emerald-50 text-emerald-900' : 'bg-rose-50 text-rose-900')} aria-live="polite">
            <p className="font-bold">{chosen === question.answer ? 'Nailed it! 🎉' : 'Not quite.'}</p>
            <p className="mt-1 text-sm">
              <RichText text={question.explanation} />
            </p>
          </div>
        )}
      </div>
      <div className="flex justify-end">
        <Button onClick={() => setIndex(index + 1)} disabled={!answered}>
          {index === total - 1 ? 'See my score' : 'Next question'}
        </Button>
      </div>
    </div>
  )
}
