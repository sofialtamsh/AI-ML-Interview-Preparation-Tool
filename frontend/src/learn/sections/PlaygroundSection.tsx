import { CircleCheck, Lightbulb, Sparkles } from 'lucide-react'
import { useState } from 'react'

import { cn } from '../../lib/cn'
import type { PlaygroundContent } from '../../lib/types'
import { RichText } from '../RichText'
import { WIDGET_COMPONENTS } from '../widgets'

export function PlaygroundSection({ playground }: { playground: PlaygroundContent }) {
  const Widget = WIDGET_COMPONENTS[playground.widget]
  const [hints, setHints] = useState<Set<number>>(new Set())
  const [done, setDone] = useState<Set<number>>(new Set())
  const toggle = (set: Set<number>, i: number) => new Set(set).add(i)

  return (
    <div className="space-y-5">
      <div>
        <h2 className="font-display text-2xl font-bold tracking-tight text-slate-900">{playground.title}</h2>
        <p className="mt-1 max-w-3xl text-slate-600">
          <RichText text={playground.intro} />
        </p>
      </div>

      <Widget />

      <section aria-labelledby="try-this">
        <div className="flex items-baseline justify-between gap-3">
          <h3 id="try-this" className="font-display text-lg font-bold text-slate-900">
            <Sparkles className="mr-1.5 inline size-5 text-brand-600" aria-hidden />
            Try this
          </h3>
          <span className="text-sm text-slate-500 tabular-nums">
            {done.size} / {playground.tasks.length} done
          </span>
        </div>
        <ol className="mt-3 grid gap-3 md:grid-cols-2">
          {playground.tasks.map((task, i) => {
            const finished = done.has(i)
            return (
              <li
                key={i}
                className={cn(
                  'rounded-2xl p-4 ring-1 transition',
                  finished ? 'bg-emerald-50/70 ring-emerald-200' : 'bg-white ring-slate-200',
                )}
              >
                <div className="flex gap-3">
                  <span
                    className={cn(
                      'grid size-7 shrink-0 place-items-center rounded-full text-sm font-bold',
                      finished ? 'bg-emerald-500 text-white' : 'bg-brand-50 text-brand-700',
                    )}
                  >
                    {finished ? <CircleCheck className="size-4" aria-label="Done" /> : i + 1}
                  </span>
                  <div className="min-w-0 flex-1 space-y-2">
                    <p className="font-medium text-slate-900">
                      <RichText text={task.prompt} />
                    </p>
                    {hints.has(i) && !finished && (
                      <p className="text-sm text-slate-600">
                        <Lightbulb className="mr-1 inline size-4 text-amber-500" aria-hidden />
                        <RichText text={task.hint} />
                      </p>
                    )}
                    {finished && (
                      <p className="animate-pop rounded-xl bg-white px-3 py-2 text-sm text-slate-800 ring-1 ring-emerald-200">
                        <span className="font-semibold text-emerald-700">What you just saw: </span>
                        <RichText text={task.insight} />
                      </p>
                    )}
                    {!finished && (
                      <div className="flex flex-wrap gap-2">
                        {!hints.has(i) && (
                          <button
                            type="button"
                            className="rounded-lg px-2 py-1 text-xs font-semibold text-slate-600 ring-1 ring-slate-200 hover:bg-slate-50"
                            onClick={() => setHints((s) => toggle(s, i))}
                          >
                            Need a hint?
                          </button>
                        )}
                        <button
                          type="button"
                          className="rounded-lg bg-slate-900 px-2.5 py-1 text-xs font-semibold text-white hover:bg-slate-700"
                          onClick={() => setDone((s) => toggle(s, i))}
                        >
                          I tried it, show the insight
                        </button>
                      </div>
                    )}
                  </div>
                </div>
              </li>
            )
          })}
        </ol>
      </section>
    </div>
  )
}
