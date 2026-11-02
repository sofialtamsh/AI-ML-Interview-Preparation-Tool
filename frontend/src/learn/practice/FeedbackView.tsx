import { Check, ChevronDown, MessageCircleQuestion, Sparkles, X } from 'lucide-react'
import { useState, type ReactNode } from 'react'

import { cn } from '../../lib/cn'
import type { AnswerFeedback, Delivery, VerdictKey } from '../../lib/types'

const VERDICT_STYLE: Record<VerdictKey, { emoji: string; ring: string; pill: string }> = {
  ready: { emoji: '🚀', ring: '#1baf7a', pill: 'bg-emerald-50 text-emerald-800 ring-emerald-200' },
  almost: { emoji: '💪', ring: '#2a78d6', pill: 'bg-sky-50 text-sky-800 ring-sky-200' },
  getting_there: { emoji: '🌱', ring: '#eda100', pill: 'bg-amber-50 text-amber-900 ring-amber-200' },
  practice: { emoji: '🔁', ring: '#eb6834', pill: 'bg-orange-50 text-orange-900 ring-orange-200' },
  off_topic: { emoji: '🧭', ring: '#e11d48', pill: 'bg-rose-50 text-rose-800 ring-rose-200' },
}

const PACE_NOTE: Record<Delivery['pace'], string> = {
  slow: 'a bit slow',
  good: 'comfy pace',
  fast: 'a bit fast',
}

export const formatClock = (seconds: number) => {
  const whole = Math.round(seconds)
  return `${Math.floor(whole / 60)}:${String(whole % 60).padStart(2, '0')}`
}

function ScoreRing({ score, verdict }: { score: number; verdict: VerdictKey }) {
  const radius = 42
  const circumference = 2 * Math.PI * radius
  return (
    <div className="relative size-28 shrink-0">
      <svg viewBox="0 0 100 100" className="size-full -rotate-90" aria-hidden>
        <circle cx="50" cy="50" r={radius} fill="none" stroke="#e2e8f0" strokeWidth="9" />
        <circle
          cx="50"
          cy="50"
          r={radius}
          fill="none"
          stroke={VERDICT_STYLE[verdict].ring}
          strokeWidth="9"
          strokeLinecap="round"
          strokeDasharray={`${(score / 10) * circumference} ${circumference}`}
        />
      </svg>
      <div className="absolute inset-0 flex flex-col items-center justify-center">
        <span className="font-display text-3xl font-bold text-slate-900 tabular-nums">{score.toFixed(1)}</span>
        <span className="text-xs font-medium text-slate-500">out of 10</span>
      </div>
    </div>
  )
}

function Meter({ label, score, comment }: { label: string; score: number; comment: string }) {
  return (
    <li>
      <div className="flex items-baseline justify-between gap-3">
        <span className="text-sm font-semibold text-slate-800">{label}</span>
        <span className="text-sm font-semibold text-slate-600 tabular-nums">{score}/5</span>
      </div>
      <div className="mt-1.5 flex gap-1" role="img" aria-label={`${label}: ${score} out of 5`}>
        {[1, 2, 3, 4, 5].map((n) => (
          <span key={n} className={cn('h-2 flex-1 rounded-full', n <= score ? 'bg-brand-600' : 'bg-slate-200')} />
        ))}
      </div>
      <p className="mt-1.5 text-sm text-slate-600">{comment}</p>
    </li>
  )
}

function Block({ title, tone = 'plain', children }: { title: ReactNode; tone?: 'plain' | 'good' | 'fix' | 'tip'; children: ReactNode }) {
  const tones = {
    plain: 'bg-white ring-slate-200',
    good: 'bg-emerald-50/60 ring-emerald-100',
    fix: 'bg-amber-50/70 ring-amber-100',
    tip: 'bg-brand-50/60 ring-brand-100',
  }
  return (
    <section className={cn('rounded-2xl p-4 ring-1', tones[tone])}>
      <h4 className="font-display text-base font-bold text-slate-900">{title}</h4>
      <div className="mt-2 text-sm text-slate-700">{children}</div>
    </section>
  )
}

function Reveal({ label, children }: { label: ReactNode; children: ReactNode }) {
  const [open, setOpen] = useState(false)
  return (
    <div className="rounded-2xl bg-white ring-1 ring-slate-200">
      <button type="button" aria-expanded={open} onClick={() => setOpen(!open)} className="flex w-full items-center justify-between gap-3 px-4 py-3 text-left font-semibold text-slate-900 hover:bg-slate-50">
        {label}
        <ChevronDown className={cn('size-4 shrink-0 text-slate-400 transition', open && 'rotate-180')} aria-hidden />
      </button>
      {open && <div className="animate-fade-up border-t border-slate-100 px-4 py-3 text-sm text-slate-700">{children}</div>}
    </div>
  )
}

export function DeliveryChips({ delivery }: { delivery: Delivery }) {
  const fillers = Object.entries(delivery.fillers)
    .map(([word, n]) => (n > 1 ? `${word} ×${n}` : word))
    .join(', ')
  const chips = [
    { emoji: '⏱️', text: formatClock(delivery.duration_s), note: 'answer length' },
    { emoji: '🗣️', text: `${delivery.wpm} wpm`, note: PACE_NOTE[delivery.pace] },
    { emoji: '🫧', text: `${delivery.filler_count} filler${delivery.filler_count === 1 ? '' : 's'}`, note: fillers || 'nice and clean' },
    ...(delivery.longest_pause_s !== null ? [{ emoji: '⏸️', text: `${delivery.longest_pause_s.toFixed(1)} s`, note: 'longest pause' }] : []),
  ]
  return (
    <ul className="grid grid-cols-2 gap-2 sm:grid-cols-4">
      {chips.map((chip) => (
        <li key={chip.note + chip.text} className="rounded-2xl bg-slate-50 px-3 py-2.5 ring-1 ring-slate-200">
          <p className="text-base font-bold text-slate-900 tabular-nums">
            <span aria-hidden>{chip.emoji}</span> {chip.text}
          </p>
          <p className="truncate text-xs text-slate-500" title={chip.note}>
            {chip.note}
          </p>
        </li>
      ))}
    </ul>
  )
}

/** The interviewer-style breakdown of one spoken answer. */
export function FeedbackView({ feedback, delivery, transcript }: { feedback: AnswerFeedback; delivery: Delivery | null; transcript: string | null }) {
  const style = VERDICT_STYLE[feedback.verdict.key]
  return (
    <div className="space-y-4">
      <div className="flex flex-col items-center gap-4 rounded-3xl bg-white p-5 text-center ring-1 ring-slate-200 sm:flex-row sm:text-left">
        <ScoreRing score={feedback.score} verdict={feedback.verdict.key} />
        <div className="min-w-0">
          <span className={cn('inline-flex items-center gap-1.5 rounded-full px-3 py-1 text-sm font-bold ring-1', style.pill)}>
            <span aria-hidden>{style.emoji}</span> {feedback.verdict.label}
          </span>
          <p className="mt-2 text-slate-700">{feedback.summary}</p>
        </div>
      </div>

      <section className="rounded-3xl bg-white p-5 ring-1 ring-slate-200">
        <h4 className="font-display text-base font-bold text-slate-900">How an interviewer would score it</h4>
        <ul className="mt-3 grid gap-4 sm:grid-cols-2">
          {feedback.criteria.map((c) => (
            <Meter key={c.key} label={c.label} score={c.score} comment={c.comment} />
          ))}
        </ul>
      </section>

      {delivery && <DeliveryChips delivery={delivery} />}

      <div className="grid gap-3 sm:grid-cols-2">
        {feedback.strengths.length > 0 && (
          <Block title="✅ What landed" tone="good">
            <ul className="space-y-2">
              {feedback.strengths.map((s, i) => (
                <li key={i}>
                  <p className="font-semibold text-slate-900">{s.point}</p>
                  <p className="text-slate-600 italic">&ldquo;{s.quote}&rdquo;</p>
                </li>
              ))}
            </ul>
          </Block>
        )}
        <Block title="🔧 Level up" tone="fix">
          <ol className="space-y-2">
            {feedback.improvements.map((item, i) => (
              <li key={i}>
                <p className="font-semibold text-slate-900">
                  {i + 1}. {item.point}
                </p>
                <p>{item.how}</p>
              </li>
            ))}
          </ol>
        </Block>
      </div>

      {(feedback.key_points_covered.length > 0 || feedback.key_points_missed.length > 0) && (
        <Block title="🎯 Key points">
          <ul className="flex flex-wrap gap-2">
            {feedback.key_points_covered.map((point) => (
              <li key={`hit-${point}`} className="inline-flex items-center gap-1 rounded-full bg-emerald-50 px-2.5 py-1 text-xs font-semibold text-emerald-800 ring-1 ring-emerald-200">
                <Check className="size-3.5" aria-label="Covered:" /> {point}
              </li>
            ))}
            {feedback.key_points_missed.map((point) => (
              <li key={`miss-${point}`} className="inline-flex items-center gap-1 rounded-full bg-rose-50 px-2.5 py-1 text-xs font-semibold text-rose-800 ring-1 ring-rose-200">
                <X className="size-3.5" aria-label="Missed:" /> {point}
              </li>
            ))}
          </ul>
        </Block>
      )}

      {feedback.mistakes.length > 0 && (
        <Block title="⚠️ Fix these" tone="fix">
          <ul className="space-y-3">
            {feedback.mistakes.map((m, i) => (
              <li key={i}>
                <p className="text-slate-600">
                  You said <span className="italic">&ldquo;{m.quote}&rdquo;</span>
                </p>
                <p className="mt-0.5 font-medium text-slate-900">→ {m.correction}</p>
              </li>
            ))}
          </ul>
        </Block>
      )}

      <Block title="💡 Pro tips" tone="tip">
        <ul className="space-y-1.5">
          {feedback.tips.map((tip, i) => (
            <li key={i} className="flex gap-2">
              <span aria-hidden>→</span>
              <span>{tip}</span>
            </li>
          ))}
        </ul>
      </Block>

      <Reveal
        label={
          <span className="inline-flex items-center gap-2">
            <Sparkles className="size-4 text-fuchsia-600" aria-hidden /> Say it like this
          </span>
        }
      >
        <p className="leading-relaxed whitespace-pre-line">{feedback.better_answer}</p>
      </Reveal>

      {feedback.follow_up && (
        <Reveal
          label={
            <span className="inline-flex items-center gap-2">
              <MessageCircleQuestion className="size-4 text-brand-600" aria-hidden /> Next they might ask: {feedback.follow_up.question}
            </span>
          }
        >
          <p>{feedback.follow_up.answer}</p>
        </Reveal>
      )}

      {transcript && (
        <Reveal label="📝 What we heard">
          <p className="leading-relaxed">{transcript}</p>
          <p className="mt-2 text-xs text-slate-500">Auto-transcribed from your voice, so small slips (and missing &ldquo;um&rdquo;s) are normal.</p>
        </Reveal>
      )}

      <p className="text-center text-xs text-slate-500">AI coach feedback can be wrong. When in doubt, trust the strong answer.</p>
    </div>
  )
}
