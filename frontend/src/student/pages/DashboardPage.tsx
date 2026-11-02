import { ArrowRight, Compass, Copy, Flame, Mic, Sparkles, Target, Trophy, Zap } from 'lucide-react'
import { Link } from 'react-router'

import { ButtonLink } from '../../components/ui/Button'
import { Alert, Card, CardHeader, EmptyState, Skeleton } from '../../components/ui/Feedback'
import { useToast } from '../../components/ui/Toast'
import { MasteryChip, ProgressBar } from '../../learn/progress'
import { SECTIONS, type ComponentKey } from '../../learn/sections'
import { errorMessage } from '../../lib/api'
import { cn } from '../../lib/cn'
import { timeAgo } from '../../lib/format'
import type { ProgressSummary, TopicSummary } from '../../lib/types'
import { useCurrentStudent } from '../api'
import { useMyProgress } from '../progressApi'

function greeting(hour = new Date().getHours()) {
  if (hour < 5) return 'Burning the midnight oil'
  if (hour < 12) return 'Good morning'
  if (hour < 17) return 'Good afternoon'
  return 'Good evening'
}

function Ring({ value }: { value: number }) {
  const radius = 42
  const circumference = 2 * Math.PI * radius
  return (
    <div className="relative size-32 shrink-0">
      <svg viewBox="0 0 100 100" className="size-full -rotate-90" aria-hidden>
        <circle cx="50" cy="50" r={radius} fill="none" stroke="#e2e8f0" strokeWidth="9" />
        <circle
          cx="50"
          cy="50"
          r={radius}
          fill="none"
          stroke="url(#ring)"
          strokeWidth="9"
          strokeLinecap="round"
          strokeDasharray={`${(value / 100) * circumference} ${circumference}`}
        />
        <defs>
          <linearGradient id="ring" x1="0" x2="1">
            <stop offset="0%" stopColor="#7c3aed" />
            <stop offset="100%" stopColor="#d946ef" />
          </linearGradient>
        </defs>
      </svg>
      <div className="absolute inset-0 flex flex-col items-center justify-center">
        <span className="font-display text-3xl font-bold text-slate-900 tabular-nums">{value}%</span>
        <span className="text-xs font-medium text-slate-500">of your path</span>
      </div>
    </div>
  )
}

const sectionLink = (topic: { slug: string }, section: string | null) =>
  `/app/learn/${topic.slug}${section && section !== 'lesson' ? `?s=${SECTIONS[section as ComponentKey]?.slug ?? ''}` : ''}`

function ContinueCard({ summary }: { summary: ProgressSummary }) {
  const item = summary.continue ?? summary.recommended[0] ?? null
  if (!item) {
    return (
      <Card className="p-5">
        <EmptyState icon={<Trophy className="size-6" />} title="You've finished everything live">
          New topics appear here as soon as they're published.
        </EmptyState>
      </Card>
    )
  }
  const resume = summary.continue !== null
  const section = resume ? summary.continue!.next_section : null
  return (
    <Card className="flex flex-col gap-4 p-5">
      <p className="text-xs font-bold tracking-wide text-brand-700 uppercase">{resume ? 'Pick up where you left off' : 'Start here'}</p>
      <div>
        <p className="text-xs font-medium text-slate-500">{item.domain}</p>
        <p className="font-display text-2xl font-bold text-slate-900">{item.name}</p>
      </div>
      <div className="space-y-1.5">
        <ProgressBar value={item.completion} label={`${item.name} progress`} />
        <p className="text-sm text-slate-600 tabular-nums">
          {item.done} of {item.total} sections done
        </p>
      </div>
      <ButtonLink to={sectionLink(item, section)} variant="glow" className="self-start">
        {section ? `Continue: ${SECTIONS[section as ComponentKey]?.label ?? 'next'}` : 'Start'} <ArrowRight className="size-4" aria-hidden />
      </ButtonLink>
    </Card>
  )
}

function TopicRow({ topic }: { topic: TopicSummary }) {
  return (
    <li>
      <Link to={sectionLink(topic, topic.completed ? null : topic.last_section)} className="group flex items-center gap-4 px-5 py-3 transition hover:bg-slate-50">
        <div className="min-w-0 flex-1 space-y-1.5">
          <div className="flex flex-wrap items-center gap-2">
            <p className="font-semibold text-slate-900">{topic.name}</p>
            {topic.completed && (
              <span className="inline-flex items-center gap-1 text-xs font-semibold text-emerald-700">
                <Trophy className="size-3.5" aria-hidden /> Done
              </span>
            )}
            <MasteryChip band={topic.mastery.band} />
          </div>
          <ProgressBar value={topic.completion} label={`${topic.name} progress`} />
        </div>
        <span className="w-20 shrink-0 text-right text-xs text-slate-500 tabular-nums">
          {topic.done}/{topic.total} done
        </span>
        <ArrowRight className="size-4 shrink-0 text-slate-400 transition group-hover:translate-x-0.5 group-hover:text-brand-600" aria-hidden />
      </Link>
    </li>
  )
}

function Stat({ icon: Icon, value, label }: { icon: typeof Flame; value: string; label: string }) {
  return (
    <div className="rounded-2xl bg-white/15 px-4 py-3 ring-1 ring-white/20 backdrop-blur">
      <p className="flex items-center gap-1.5 font-display text-2xl font-bold tabular-nums">
        <Icon className="size-5" aria-hidden /> {value}
      </p>
      <p className="text-xs font-medium text-white/80">{label}</p>
    </div>
  )
}

export default function DashboardPage() {
  const student = useCurrentStudent()
  const progress = useMyProgress()
  const toast = useToast()
  const firstName = student.full_name.split(' ')[0]
  const data = progress.data

  const copyId = async () => {
    try {
      await navigator.clipboard.writeText(student.student_code)
      toast.success('Student ID copied')
    } catch {
      toast.error('Could not copy. Your ID is ' + student.student_code)
    }
  }

  return (
    <div className="space-y-6">
      <section className="relative animate-fade-up overflow-hidden rounded-3xl bg-gradient-to-br from-brand-600 via-violet-600 to-fuchsia-600 px-6 py-8 text-white shadow-xl shadow-brand-600/20 sm:px-10">
        <div aria-hidden className="absolute -top-16 -right-10 size-64 animate-float rounded-full bg-white/15 blur-2xl" />
        <div className="relative">
          <p className="text-sm font-medium text-white/75">{greeting()},</p>
          <h1 className="mt-1 font-display text-3xl font-bold tracking-tight sm:text-4xl">
            {firstName} <span aria-hidden>👋</span>
          </h1>
          {data && (
            <div className="mt-5 grid max-w-2xl grid-cols-2 gap-3 sm:grid-cols-4">
              <Stat icon={Flame} value={String(data.activity.streak_days)} label="day streak" />
              <Stat icon={Target} value={`${data.overall_completion}%`} label="of your path done" />
              <Stat icon={Zap} value={data.quiz_average !== null ? `${Math.round(data.quiz_average)}%` : '—'} label="quiz average" />
              <Stat icon={Mic} value={String(data.interview.answers_recorded)} label="answers practised" />
            </div>
          )}
          <div className="mt-6 flex flex-wrap items-center gap-3">
            <ButtonLink to="/app/learn" variant="secondary" className="shadow-lg">
              <Compass className="size-4" aria-hidden /> Explore topics
            </ButtonLink>
            <button
              type="button"
              onClick={copyId}
              className="inline-flex items-center gap-2 rounded-full bg-white/15 px-3.5 py-1.5 font-mono text-sm ring-1 ring-white/25 backdrop-blur transition hover:bg-white/25"
              aria-label={`Copy student ID ${student.student_code}`}
            >
              {student.student_code}
              <Copy className="size-3.5" aria-hidden />
            </button>
          </div>
        </div>
      </section>

      {progress.isPending && (
        <div className="grid gap-6 lg:grid-cols-3">
          <Skeleton className="h-56 rounded-2xl" />
          <Skeleton className="h-56 rounded-2xl lg:col-span-2" />
        </div>
      )}
      {progress.isError && <Alert>{errorMessage(progress.error)}</Alert>}

      {data && data.topics.length === 0 && (
        <Card>
          <EmptyState icon={<Sparkles className="size-6" />} title="Your topics are on the way">
            Our team is preparing the first AI/ML topics. They&apos;ll appear here as soon as they&apos;re published.
          </EmptyState>
        </Card>
      )}

      {data && data.topics.length > 0 && (
        <>
          <div className="grid gap-6 lg:grid-cols-3">
            <ContinueCard summary={data} />
            <Card className="lg:col-span-2">
              <CardHeader title="Your progress" description="Sections you've finished, per domain. Quizzes and practice show how well you know each topic." />
              <div className="flex flex-col items-center gap-6 p-5 sm:flex-row">
                <Ring value={data.overall_completion} />
                <ul className="w-full space-y-3">
                  {data.domains.map((domain) => (
                    <li key={domain.name} className="space-y-1">
                      <div className="flex justify-between text-sm">
                        <span className="font-medium text-slate-800">{domain.name}</span>
                        <span className="text-slate-500 tabular-nums">{domain.completion}%</span>
                      </div>
                      <ProgressBar value={domain.completion} label={`${domain.name} progress`} />
                    </li>
                  ))}
                  <li className="text-sm text-slate-600">
                    {data.topics_completed} of {data.topics.length} topics complete · {data.sections_done} of {data.sections_total} sections
                  </li>
                </ul>
              </div>
            </Card>
          </div>

          <div className="grid gap-6 lg:grid-cols-3">
            <Card className="overflow-hidden lg:col-span-2">
              <CardHeader title="Your topics" description="Completion is what you've gone through; the chip is how well you know it." />
              <ul className="divide-y divide-slate-100">
                {data.topics.map((topic) => (
                  <TopicRow key={topic.slug} topic={topic} />
                ))}
              </ul>
            </Card>

            <div className="space-y-6">
              <Card className="p-5">
                <h2 className="font-display text-base font-semibold text-slate-900">Strengths & weak spots</h2>
                {data.strengths.length === 0 && data.weaknesses.length === 0 ? (
                  <p className="mt-2 text-sm text-slate-600">Take a few quizzes or practise interview answers and we&apos;ll show what you&apos;re strong at.</p>
                ) : (
                  <div className="mt-3 space-y-3 text-sm">
                    {data.strengths.length > 0 && (
                      <div>
                        <p className="text-xs font-bold tracking-wide text-emerald-700 uppercase">Strong</p>
                        <p className="text-slate-800">{data.strengths.join(', ')}</p>
                      </div>
                    )}
                    {data.weaknesses.length > 0 && (
                      <div>
                        <p className="text-xs font-bold tracking-wide text-amber-800 uppercase">Needs work</p>
                        <p className="text-slate-800">{data.weaknesses.join(', ')}</p>
                      </div>
                    )}
                  </div>
                )}
              </Card>

              {data.recommended.length > 0 && (
                <Card className="p-5">
                  <h2 className="font-display text-base font-semibold text-slate-900">Recommended next</h2>
                  <ul className="mt-3 space-y-2">
                    {data.recommended.map((topic) => (
                      <li key={topic.slug + topic.reason}>
                        <Link to={sectionLink(topic, null)} className="group flex items-center justify-between gap-3 rounded-xl bg-slate-50 px-3 py-2.5 hover:bg-brand-50">
                          <span>
                            <span className="block text-xs font-medium text-brand-700">{topic.reason}</span>
                            <span className="font-semibold text-slate-900">{topic.name}</span>
                          </span>
                          <ArrowRight className="size-4 text-slate-400 group-hover:text-brand-600" aria-hidden />
                        </Link>
                      </li>
                    ))}
                  </ul>
                </Card>
              )}
            </div>
          </div>

          <div className="grid gap-6 lg:grid-cols-2">
            <Card className="overflow-hidden">
              <CardHeader title="Recent quiz scores" description="Every attempt is kept, so you can see yourself improve." />
              {data.recent_quizzes.length === 0 ? (
                <p className="px-5 pb-5 text-sm text-slate-600">No quizzes yet. Each topic ends with one.</p>
              ) : (
                <ul className="divide-y divide-slate-100">
                  {data.recent_quizzes.map((quiz) => (
                    <li key={quiz.submitted_at + quiz.topic} className="flex items-center gap-3 px-5 py-3">
                      <span
                        className={cn(
                          'w-14 rounded-full px-2 py-0.5 text-center text-sm font-bold tabular-nums',
                          quiz.score_pct >= 75 ? 'bg-emerald-100 text-emerald-800' : quiz.score_pct >= 50 ? 'bg-sky-100 text-sky-800' : 'bg-amber-100 text-amber-900',
                        )}
                      >
                        {Math.round(quiz.score_pct)}%
                      </span>
                      <span className="min-w-0 flex-1">
                        <span className="block truncate font-medium text-slate-900">{quiz.topic}</span>
                        <span className="text-xs text-slate-500">
                          {quiz.correct}/{quiz.total} · attempt {quiz.attempt_number} · {timeAgo(quiz.submitted_at)}
                        </span>
                      </span>
                    </li>
                  ))}
                </ul>
              )}
            </Card>

            <Card className="p-5">
              <h2 className="font-display text-base font-semibold text-slate-900">Interview practice</h2>
              <dl className="mt-4 grid grid-cols-3 gap-3 text-center">
                <div className="rounded-2xl bg-slate-50 px-2 py-3">
                  <dt className="text-xs text-slate-500">Answers recorded</dt>
                  <dd className="font-display text-2xl font-bold text-slate-900 tabular-nums">{data.interview.answers_recorded}</dd>
                </div>
                <div className="rounded-2xl bg-slate-50 px-2 py-3">
                  <dt className="text-xs text-slate-500">AI-scored</dt>
                  <dd className="font-display text-2xl font-bold text-slate-900 tabular-nums">{data.interview.feedback_count}</dd>
                </div>
                <div className="rounded-2xl bg-slate-50 px-2 py-3">
                  <dt className="text-xs text-slate-500">Average</dt>
                  <dd className="font-display text-2xl font-bold text-slate-900 tabular-nums">
                    {data.interview.average_score !== null ? data.interview.average_score.toFixed(1) : '—'}
                  </dd>
                </div>
              </dl>
              {data.interview.recent_scores.length > 0 ? (
                <div className="mt-4">
                  <p className="text-xs font-medium text-slate-500">Your last {data.interview.recent_scores.length} scores (out of 10)</p>
                  <ol className="mt-2 flex h-20 items-end gap-1.5" aria-label="Recent interview practice scores">
                    {data.interview.recent_scores.map((point, i) => (
                      <li key={i} className="flex flex-1 flex-col items-center justify-end gap-1" title={`${point.score.toFixed(1)} · ${timeAgo(point.at)}`}>
                        <span className="text-[10px] font-semibold text-slate-600 tabular-nums">{point.score.toFixed(1)}</span>
                        <span className="w-full rounded-t-md bg-brand-500" style={{ height: `${Math.max(point.score * 6, 4)}px` }} />
                      </li>
                    ))}
                  </ol>
                </div>
              ) : (
                <p className="mt-4 text-sm text-slate-600">Open any topic&apos;s Interview tab and record an answer to see your scores here.</p>
              )}
            </Card>
          </div>
        </>
      )}
    </div>
  )
}
