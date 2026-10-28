import { ChevronDown, Target } from 'lucide-react'
import { useState } from 'react'

import { Badge } from '../../components/ui/Feedback'
import { cn } from '../../lib/cn'
import type { InterviewContent, InterviewEntry } from '../../lib/types'
import { RichText } from '../RichText'
import { Choice } from '../widgets/controls'

type Level = InterviewEntry['level'] | 'all'

const LABEL_TONE: Record<InterviewEntry['label'], 'neutral' | 'success' | 'warning'> = {
  'Practice question': 'neutral',
  'Asked in real interviews': 'success',
  'In demand right now': 'warning',
}

const LEVEL_TONE: Record<InterviewEntry['level'], string> = {
  basic: 'bg-emerald-500',
  intermediate: 'bg-amber-500',
  advanced: 'bg-rose-500',
}

function QuestionCard({ item, number }: { item: InterviewEntry; number: number }) {
  const [open, setOpen] = useState(false)
  return (
    <li className="overflow-hidden rounded-3xl bg-white ring-1 ring-slate-200">
      <button type="button" aria-expanded={open} onClick={() => setOpen(!open)} className="flex w-full gap-3 p-4 text-left hover:bg-slate-50 sm:p-5">
        <span className="font-display text-sm font-bold text-slate-400 tabular-nums">Q{number}</span>
        <span className="min-w-0 flex-1">
          <span className="flex flex-wrap items-center gap-1.5">
            <span className="inline-flex items-center gap-1 text-xs font-semibold text-slate-600 capitalize">
              <span aria-hidden className={cn('size-2 rounded-full', LEVEL_TONE[item.level])} />
              {item.level}
            </span>
            <Badge className="capitalize">{item.kind}</Badge>
            <Badge tone={LABEL_TONE[item.label]}>{item.label}</Badge>
            {item.asked_for_role && <Badge tone="brand">{item.asked_for_role}</Badge>}
          </span>
          <span className="mt-1.5 block font-semibold text-slate-900">
            <RichText text={item.question} />
          </span>
        </span>
        <ChevronDown className={cn('mt-1 size-5 shrink-0 text-slate-400 transition', open && 'rotate-180')} aria-hidden />
      </button>
      {open && (
        <div className="animate-fade-up space-y-3 border-t border-slate-100 p-4 sm:p-5">
          <div>
            <p className="text-xs font-bold tracking-wide text-brand-700 uppercase">Strong answer</p>
            <p className="mt-1 text-slate-800">
              <RichText text={item.answer} />
            </p>
          </div>
          <div className="rounded-2xl bg-amber-50 px-4 py-3 ring-1 ring-amber-100">
            <p className="flex items-center gap-1.5 text-xs font-bold tracking-wide text-amber-800 uppercase">
              <Target className="size-3.5" aria-hidden /> What the interviewer wants
            </p>
            <p className="mt-1 text-sm text-slate-800">
              <RichText text={item.interviewer_wants} />
            </p>
          </div>
          {item.follow_ups.length > 0 && (
            <div>
              <p className="text-xs font-bold tracking-wide text-slate-500 uppercase">Likely follow-ups</p>
              <ul className="mt-2 space-y-2">
                {item.follow_ups.map((f, i) => (
                  <li key={i}>
                    <details className="group rounded-2xl bg-slate-50 px-4 py-2.5">
                      <summary className="cursor-pointer font-medium text-slate-900 marker:text-slate-400">
                        <RichText text={f.question} />
                      </summary>
                      <p className="mt-2 text-sm text-slate-700">
                        <RichText text={f.answer} />
                      </p>
                    </details>
                  </li>
                ))}
              </ul>
            </div>
          )}
        </div>
      )}
    </li>
  )
}

export function InterviewSection({ interview }: { interview: InterviewContent }) {
  const [level, setLevel] = useState<Level>('all')
  const shown = interview.questions.filter((q) => level === 'all' || q.level === level)
  const count = (l: InterviewEntry['level']) => interview.questions.filter((q) => q.level === l).length
  return (
    <div className="space-y-5">
      <Choice
        label="Level"
        value={level}
        onChange={setLevel}
        options={[
          { value: 'all', label: `All (${interview.questions.length})` },
          { value: 'basic', label: `Basic (${count('basic')})` },
          { value: 'intermediate', label: `Intermediate (${count('intermediate')})` },
          { value: 'advanced', label: `Advanced (${count('advanced')})` },
        ]}
      />
      <p className="text-sm text-slate-500">Say your answer out loud first, then open the card to compare.</p>
      <ol className="space-y-3">
        {shown.map((item) => (
          <QuestionCard key={item.question} item={item} number={interview.questions.indexOf(item) + 1} />
        ))}
      </ol>
      <section className="rounded-3xl bg-gradient-to-br from-brand-600 to-fuchsia-600 p-5 text-white">
        <h3 className="font-display text-lg font-bold">🎯 Interview takeaways</h3>
        <ul className="mt-2 space-y-1.5">
          {interview.takeaways.map((t, i) => (
            <li key={i} className="flex gap-2">
              <span aria-hidden>→</span>
              <span>
                <RichText text={t} />
              </span>
            </li>
          ))}
        </ul>
      </section>
    </div>
  )
}
