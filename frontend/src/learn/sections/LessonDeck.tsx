import { ChevronLeft, ChevronRight, GalleryHorizontal, Rows3 } from 'lucide-react'
import { useEffect, useRef, useState, type ReactNode } from 'react'

import { Button } from '../../components/ui/Button'
import { cn } from '../../lib/cn'
import type { Lesson, LessonCard } from '../../lib/types'
import { FigureView } from '../Figures'
import { RichText } from '../RichText'

const KINDS: Record<LessonCard['kind'], { label: string; tone: string }> = {
  hook: { label: 'Hook', tone: 'from-fuchsia-500 to-brand-600' },
  tldr: { label: 'TL;DR', tone: 'from-amber-400 to-orange-500' },
  intuition: { label: 'The intuition', tone: 'from-sky-500 to-brand-600' },
  analogy: { label: 'Analogy', tone: 'from-emerald-500 to-teal-600' },
  steps: { label: 'Step by step', tone: 'from-indigo-500 to-brand-600' },
  math: { label: 'The math', tone: 'from-slate-700 to-slate-900' },
  example: { label: 'Example', tone: 'from-cyan-500 to-sky-600' },
  myth: { label: 'Myth vs fact', tone: 'from-rose-500 to-fuchsia-600' },
  interview: { label: 'Interview angle', tone: 'from-violet-500 to-brand-700' },
  recap: { label: 'Recap', tone: 'from-emerald-500 to-brand-600' },
}

export function CardView({ card, index, total }: { card: LessonCard; index: number; total: number }) {
  const kind = KINDS[card.kind]
  return (
    <article className="flex h-full flex-col overflow-hidden rounded-3xl bg-white shadow-sm ring-1 ring-slate-200">
      <div className={cn('h-1.5 bg-gradient-to-r', kind.tone)} />
      <div className="flex flex-1 flex-col gap-4 p-5 sm:p-7">
        <div className="flex items-center justify-between gap-3">
          <span className={cn('rounded-full bg-gradient-to-r px-2.5 py-0.5 text-xs font-bold text-white', kind.tone)}>{kind.label}</span>
          <span className="text-xs font-medium text-slate-400 tabular-nums">
            {index + 1} / {total}
          </span>
        </div>
        <h3 className="font-display text-2xl font-bold tracking-tight text-slate-900 sm:text-3xl">
          {card.emoji && <span className="mr-2">{card.emoji}</span>}
          {card.title}
        </h3>
        {card.figure && (
          <div className="rounded-2xl bg-slate-50 p-3 ring-1 ring-slate-100">
            <FigureView name={card.figure} className="mx-auto block max-h-56 w-full" />
          </div>
        )}
        {card.body && (
          <p className="text-base leading-relaxed text-slate-700 sm:text-lg">
            <RichText text={card.body} />
          </p>
        )}
        {card.formula && (
          <div className="rounded-2xl bg-slate-900 px-4 py-4 text-center font-mono text-lg text-white sm:text-xl">{card.formula}</div>
        )}
        {card.symbols.length > 0 && (
          <dl className="grid gap-2 sm:grid-cols-2">
            {card.symbols.map((s) => (
              <div key={s.symbol} className="flex items-baseline gap-3 rounded-xl bg-slate-50 px-3 py-2">
                <dt className="min-w-8 font-mono font-bold text-brand-700">{s.symbol}</dt>
                <dd className="text-sm text-slate-700">
                  <RichText text={s.meaning} />
                </dd>
              </div>
            ))}
          </dl>
        )}
        {card.myth && card.fact && (
          <div className="grid gap-2 sm:grid-cols-2">
            <div className="rounded-2xl bg-rose-50 p-4 ring-1 ring-rose-100">
              <p className="text-xs font-bold tracking-wide text-rose-700 uppercase">❌ Myth</p>
              <p className="mt-1 text-slate-800">
                <RichText text={card.myth} />
              </p>
            </div>
            <div className="rounded-2xl bg-emerald-50 p-4 ring-1 ring-emerald-100">
              <p className="text-xs font-bold tracking-wide text-emerald-700 uppercase">✅ Fact</p>
              <p className="mt-1 text-slate-800">
                <RichText text={card.fact} />
              </p>
            </div>
          </div>
        )}
        {card.bullets.length > 0 && (
          <ul className="space-y-2">
            {card.bullets.map((bullet, i) => (
              <li key={i} className="flex gap-3 text-slate-700">
                <span aria-hidden className={cn('mt-2 size-2 shrink-0 rounded-full bg-gradient-to-r', kind.tone)} />
                <span>
                  <RichText text={bullet} />
                </span>
              </li>
            ))}
          </ul>
        )}
      </div>
    </article>
  )
}

export function LessonDeck({ lesson, after }: { lesson: Lesson; after?: ReactNode }) {
  const [index, setIndex] = useState(0)
  const [all, setAll] = useState(false)
  const swipe = useRef<number | null>(null)
  const total = lesson.cards.length
  const last = index === total - 1

  const go = (next: number) => setIndex(Math.max(0, Math.min(total - 1, next)))

  useEffect(() => {
    if (all) return
    const onKey = (event: KeyboardEvent) => {
      const target = event.target as HTMLElement
      if (target.closest('input, textarea, select, [role="slider"]')) return
      if (event.key === 'ArrowRight') setIndex((i) => Math.min(total - 1, i + 1))
      if (event.key === 'ArrowLeft') setIndex((i) => Math.max(0, i - 1))
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [all, total])

  const keyTerms = (
    <section className="rounded-3xl bg-white p-5 ring-1 ring-slate-200">
      <h3 className="font-display text-lg font-bold text-slate-900">Key terms</h3>
      <dl className="mt-3 grid gap-2 sm:grid-cols-2">
        {lesson.key_terms.map((term) => (
          <div key={term.term} className="rounded-xl bg-slate-50 px-3 py-2">
            <dt className="font-semibold text-slate-900">{term.term}</dt>
            <dd className="text-sm text-slate-600">
              <RichText text={term.meaning} />
            </dd>
          </div>
        ))}
      </dl>
    </section>
  )

  return (
    <div className="space-y-4">
      <div className="flex justify-end">
        <Button
          size="sm"
          variant="ghost"
          icon={all ? <GalleryHorizontal className="size-4" /> : <Rows3 className="size-4" />}
          onClick={() => setAll(!all)}
        >
          {all ? 'One card at a time' : 'Show all cards'}
        </Button>
      </div>

      {all ? (
        <div className="space-y-4">
          {lesson.cards.map((card, i) => (
            <CardView key={i} card={card} index={i} total={total} />
          ))}
          {keyTerms}
          {after}
        </div>
      ) : (
        <>
          <div
            className="mx-auto max-w-3xl touch-pan-y"
            onPointerDown={(event) => (swipe.current = event.clientX)}
            onPointerUp={(event) => {
              if (swipe.current === null) return
              const dx = event.clientX - swipe.current
              swipe.current = null
              if (Math.abs(dx) > 60) go(index + (dx < 0 ? 1 : -1))
            }}
          >
            <div key={index} className="animate-fade-up">
              <CardView card={lesson.cards[index]} index={index} total={total} />
            </div>
          </div>
          <div className="mx-auto flex max-w-3xl items-center justify-between gap-3">
            <Button variant="secondary" icon={<ChevronLeft className="size-4" />} onClick={() => go(index - 1)} disabled={index === 0}>
              Back
            </Button>
            <div className="hidden flex-wrap justify-center gap-1.5 sm:flex" role="group" aria-label="Cards">
              {lesson.cards.map((card, i) => (
                <button
                  key={i}
                  type="button"
                  aria-current={i === index ? 'step' : undefined}
                  aria-label={`Card ${i + 1}: ${card.title}`}
                  onClick={() => setIndex(i)}
                  className={cn('h-2 rounded-full transition-all', i === index ? 'w-6 bg-brand-600' : 'w-2 bg-slate-300 hover:bg-slate-400')}
                />
              ))}
            </div>
            <Button onClick={() => go(index + 1)} disabled={last}>
              Next <ChevronRight className="size-4" />
            </Button>
          </div>
          {last && (
            <div className="mx-auto max-w-3xl space-y-4">
              {keyTerms}
              {after}
            </div>
          )}
        </>
      )}
    </div>
  )
}
