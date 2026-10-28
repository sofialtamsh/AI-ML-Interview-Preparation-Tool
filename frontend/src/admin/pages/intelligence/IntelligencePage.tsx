import { Brain, Check, FileSearch, Search, TriangleAlert, X } from 'lucide-react'
import { useEffect, useMemo, useState } from 'react'
import { Link, useSearchParams } from 'react-router'

import { Pagination } from '../../../components/Pagination'
import { Button } from '../../../components/ui/Button'
import { Alert, Badge, Card, EmptyState, PageHeader, Skeleton } from '../../../components/ui/Feedback'
import { SelectField } from '../../../components/ui/Field'
import { StatTile } from '../../../components/ui/StatTile'
import { useToast } from '../../../components/ui/Toast'
import { errorMessage } from '../../../lib/api'
import { cn } from '../../../lib/cn'
import { formatCount, formatDay, timeAgo } from '../../../lib/format'
import type { InterviewQuestion, TopicInsight } from '../../../lib/types'
import { useCan } from '../../api'
import {
  useBulkReview,
  useIntelligenceSummary,
  useQuestions,
  useReviewQuestion,
  useTaxonomy,
  useTopicInsights,
  type QuestionFilters,
} from '../../intelApi'
import { SIGNALS, TrendBadge } from '../agents/shared'
import { QuestionDialog } from './QuestionDialog'

type Tab = 'review' | 'approved' | 'topics'

function useDebounced(value: string, ms = 300) {
  const [debounced, setDebounced] = useState(value)
  useEffect(() => {
    const timer = window.setTimeout(() => setDebounced(value), ms)
    return () => window.clearTimeout(timer)
  }, [value, ms])
  return debounced
}

function SearchBox({ value, onChange, placeholder }: { value: string; onChange: (v: string) => void; placeholder: string }) {
  return (
    <label className="relative w-full sm:w-72">
      <span className="sr-only">{placeholder}</span>
      <Search className="pointer-events-none absolute top-1/2 left-3 size-4 -translate-y-1/2 text-slate-400" aria-hidden />
      <input
        type="search"
        value={value}
        onChange={(e) => onChange(e.target.value)}
        placeholder={placeholder}
        className="w-full rounded-xl border-0 bg-white py-2 pr-3 pl-9 text-sm ring-1 ring-slate-300 ring-inset focus:ring-2 focus:ring-brand-500 focus:outline-none"
      />
    </label>
  )
}

function QuestionBadges({ question }: { question: InterviewQuestion }) {
  return (
    <span className="mt-1.5 flex flex-wrap gap-1">
      {question.topic ? <Badge tone="brand">{question.topic.name}</Badge> : <Badge>No topic</Badge>}
      {!question.grounded && (
        <Badge tone="warning">
          <TriangleAlert className="size-3" aria-hidden /> Not word-for-word
        </Badge>
      )}
      {question.duplicate_of_id && <Badge>Possible repeat</Badge>}
      {question.round && <Badge>{question.round}</Badge>}
    </span>
  )
}

/** Pending questions, grouped by the interview they came from. */
function ReviewQueue({ onOpen }: { onOpen: (id: string) => void }) {
  const canReview = useCan('intelligence.review')
  const [search, setSearch] = useState('')
  const [notGrounded, setNotGrounded] = useState(false)
  const [page, setPage] = useState(1)
  const q = useDebounced(search)
  const filters: QuestionFilters = {
    status: 'pending_review',
    topicId: '',
    sourceId: '',
    q,
    hideDuplicates: false,
    notGrounded,
    page,
    pageSize: 40,
  }
  const questions = useQuestions(filters)
  const bulk = useBulkReview()
  const review = useReviewQuestion()
  const toast = useToast()
  useEffect(() => setPage(1), [q, notGrounded])

  const groups = useMemo(() => {
    const byInterview = new Map<string, InterviewQuestion[]>()
    for (const question of questions.data?.items ?? []) {
      const list = byInterview.get(question.experience.id) ?? []
      list.push(question)
      byInterview.set(question.experience.id, list)
    }
    return [...byInterview.values()]
  }, [questions.data])

  const decide = (ids: string[], status: 'approved' | 'rejected') =>
    bulk.mutate(
      { question_ids: ids, status },
      {
        onSuccess: (r) => toast.success(`${status === 'approved' ? 'Approved' : 'Rejected'} ${r.updated} question${r.updated === 1 ? '' : 's'}`),
        onError: (e) => toast.error(errorMessage(e)),
      },
    )

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <SearchBox value={search} onChange={setSearch} placeholder="Search questions, companies, roles" />
        <label className="inline-flex cursor-pointer items-center gap-2 text-sm text-slate-600">
          <input type="checkbox" className="size-4 accent-brand-600" checked={notGrounded} onChange={(e) => setNotGrounded(e.target.checked)} />
          Only questions not word-for-word in the source
        </label>
      </div>
      {questions.isPending ? (
        <Skeleton className="h-40 rounded-2xl" />
      ) : questions.isError ? (
        <Alert>{errorMessage(questions.error)}</Alert>
      ) : groups.length === 0 ? (
        <Card>
          <EmptyState icon={<Check className="size-6" />} title={q || notGrounded ? 'Nothing matches' : 'Nothing waiting for review'}>
            {q || notGrounded ? (
              'Try another search.'
            ) : (
              <>
                Questions appear here after the{' '}
                <Link to="/admin/agents/exploration" className="font-semibold text-brand-700 hover:underline">
                  Exploration agent
                </Link>{' '}
                reads your interview records.
              </>
            )}
          </EmptyState>
        </Card>
      ) : (
        <>
          {groups.map((group) => {
            const e = group[0].experience
            return (
              <Card key={e.id} className="overflow-hidden">
                <div className="flex flex-wrap items-start justify-between gap-3 border-b border-slate-100 px-5 py-3.5">
                  <div className="min-w-0">
                    <p className="font-semibold text-slate-900">
                      {e.role ?? 'Role not stated'}
                      <span className="font-normal text-slate-500"> · {e.company ?? 'Company not stated'}</span>
                    </p>
                    <p className="truncate text-xs text-slate-500">
                      {[e.interview_date ? formatDay(e.interview_date) : e.period, group[0].source.name, group[0].record.title]
                        .filter(Boolean)
                        .join(' · ')}
                    </p>
                  </div>
                  {canReview && (
                    <div className="flex gap-2">
                      <Button variant="ghost" size="sm" onClick={() => decide(group.map((x) => x.id), 'rejected')} disabled={bulk.isPending}>
                        Reject all
                      </Button>
                      <Button variant="secondary" size="sm" icon={<Check className="size-3.5" />} onClick={() => decide(group.map((x) => x.id), 'approved')} disabled={bulk.isPending}>
                        Approve all
                      </Button>
                    </div>
                  )}
                </div>
                <ul className="divide-y divide-slate-100">
                  {group.map((question) => (
                    <li key={question.id} className="flex items-start gap-3 px-5 py-3">
                      <button type="button" onClick={() => onOpen(question.id)} className="min-w-0 flex-1 text-left">
                        <span className="block text-sm text-slate-900 hover:text-brand-700">{question.original_text}</span>
                        <QuestionBadges question={question} />
                      </button>
                      {canReview && (
                        <span className="flex shrink-0 gap-1">
                          <button
                            type="button"
                            onClick={() => review.mutate({ id: question.id, status: 'rejected' })}
                            className="grid size-8 place-items-center rounded-lg text-slate-400 ring-1 ring-slate-200 transition hover:bg-rose-50 hover:text-rose-600"
                            aria-label="Reject"
                            title="Reject"
                          >
                            <X className="size-4" />
                          </button>
                          <button
                            type="button"
                            onClick={() => review.mutate({ id: question.id, status: 'approved' })}
                            className="grid size-8 place-items-center rounded-lg text-emerald-600 ring-1 ring-emerald-200 transition hover:bg-emerald-50"
                            aria-label="Approve"
                            title="Approve"
                          >
                            <Check className="size-4" />
                          </button>
                        </span>
                      )}
                    </li>
                  ))}
                </ul>
              </Card>
            )
          })}
          {questions.data.total > 40 && (
            <Card>
              <Pagination page={page} pageSize={40} total={questions.data.total} onPage={setPage} />
            </Card>
          )}
        </>
      )}
    </div>
  )
}

function ApprovedQuestions({ onOpen }: { onOpen: (id: string) => void }) {
  const taxonomy = useTaxonomy()
  const [search, setSearch] = useState('')
  const [topicId, setTopicId] = useState('')
  const [status, setStatus] = useState<'approved' | 'rejected'>('approved')
  const [page, setPage] = useState(1)
  const q = useDebounced(search)
  const questions = useQuestions({ status, topicId, sourceId: '', q, hideDuplicates: status === 'approved', notGrounded: false, page, pageSize: 20 })
  useEffect(() => setPage(1), [q, topicId, status])

  return (
    <Card className="overflow-hidden">
      <div className="flex flex-wrap items-center gap-3 border-b border-slate-100 px-5 py-4">
        <SearchBox value={search} onChange={setSearch} placeholder="Search questions, companies, roles" />
        <div className="w-full sm:w-56">
          <SelectField label="Topic" hideLabel value={topicId} onChange={(e) => setTopicId(e.target.value)}>
            <option value="">All topics</option>
            {taxonomy.data?.map((d) => (
              <optgroup key={d.id} label={d.name}>
                {d.topics.map((t) => (
                  <option key={t.id} value={t.id}>
                    {t.name}
                  </option>
                ))}
              </optgroup>
            ))}
          </SelectField>
        </div>
        <div className="w-full sm:w-40">
          <SelectField label="Status" hideLabel value={status} onChange={(e) => setStatus(e.target.value as 'approved' | 'rejected')}>
            <option value="approved">Approved</option>
            <option value="rejected">Rejected</option>
          </SelectField>
        </div>
      </div>
      {questions.isPending ? (
        <div className="p-5">
          <Skeleton className="h-24" />
        </div>
      ) : questions.isError ? (
        <div className="p-5">
          <Alert>{errorMessage(questions.error)}</Alert>
        </div>
      ) : questions.data.items.length === 0 ? (
        <EmptyState icon={<FileSearch className="size-6" />} title={`No ${status} questions${q || topicId ? ' match' : ' yet'}`}>
          {status === 'approved' ? 'Approved questions are the only ones that count as interview evidence.' : undefined}
        </EmptyState>
      ) : (
        <>
          <ul className="divide-y divide-slate-100">
            {questions.data.items.map((question) => (
              <li key={question.id}>
                <button type="button" onClick={() => onOpen(question.id)} className="flex w-full items-start gap-4 px-5 py-3 text-left transition hover:bg-slate-50">
                  <span className="min-w-0 flex-1">
                    <span className="block text-sm text-slate-900">{question.original_text}</span>
                    <span className="mt-0.5 block truncate text-xs text-slate-500">
                      {[question.experience.role, question.experience.company, question.source.name].filter(Boolean).join(' · ')}
                    </span>
                    <QuestionBadges question={question} />
                  </span>
                  {status === 'approved' && (
                    <span className="shrink-0 text-right text-xs text-slate-500">
                      <span className="block font-display text-lg font-semibold text-slate-900 tabular-nums">{question.seen_in_records}</span>
                      record{question.seen_in_records === 1 ? '' : 's'}
                    </span>
                  )}
                </button>
              </li>
            ))}
          </ul>
          {questions.data.total > 20 && <Pagination page={page} pageSize={20} total={questions.data.total} onPage={setPage} />}
        </>
      )}
    </Card>
  )
}

const TOPIC_GRID = 'sm:grid-cols-[minmax(0,1.6fr)_minmax(0,1.4fr)_minmax(0,1.1fr)_9.5rem]'

function SignalBadge({ signal }: { signal: TopicInsight['signal'] }) {
  return (
    <Badge tone={SIGNALS[signal].tone}>
      <span title={SIGNALS[signal].help}>{SIGNALS[signal].label}</span>
    </Badge>
  )
}

function TopicsView() {
  const insights = useTopicInsights()
  const [onlyEvidence, setOnlyEvidence] = useState(true)
  const domains = useMemo(() => {
    const grouped = new Map<string, TopicInsight[]>()
    for (const item of insights.data ?? []) {
      if (onlyEvidence && item.signal === 'no_evidence') continue
      const list = grouped.get(item.topic.domain_name) ?? []
      list.push(item)
      grouped.set(item.topic.domain_name, list)
    }
    return [...grouped.entries()]
  }, [insights.data, onlyEvidence])
  const maxRecords = Math.max(1, ...(insights.data ?? []).map((t) => t.interview_records))

  return (
    <div className="space-y-4">
      <Card className="p-4 text-sm text-slate-600">
        <p>
          <strong className="text-slate-900">Interview evidence</strong> counts only approved questions and the distinct records
          they came from. <strong className="text-slate-900">Market</strong> shows the trend in the most recent research finding
          about the topic. The label says which kinds of evidence point at a topic; it is not a score.
        </p>
        <div className="mt-3 flex flex-wrap gap-2">
          {Object.entries(SIGNALS).map(([key, s]) => (
            <Badge key={key} tone={s.tone} className="cursor-help">
              <span title={s.help}>{s.label}</span>
            </Badge>
          ))}
        </div>
      </Card>
      <label className="inline-flex cursor-pointer items-center gap-2 text-sm text-slate-600">
        <input type="checkbox" className="size-4 accent-brand-600" checked={onlyEvidence} onChange={(e) => setOnlyEvidence(e.target.checked)} />
        Only topics with evidence
      </label>
      {insights.isPending ? (
        <Skeleton className="h-64 rounded-2xl" />
      ) : insights.isError ? (
        <Alert>{errorMessage(insights.error)}</Alert>
      ) : domains.length === 0 ? (
        <Card>
          <EmptyState icon={<Brain className="size-6" />} title="No topics with evidence yet">
            Approve interview questions or run market research to see topics here. Untick the box above to
            see every topic in the taxonomy.
          </EmptyState>
        </Card>
      ) : (
        domains.map(([domain, items]) => (
          <Card key={domain} className="overflow-hidden">
            <h3 className="border-b border-slate-100 px-5 py-3 font-display text-sm font-semibold text-slate-900">{domain}</h3>
            {/* Fixed column fractions keep columns aligned across domains; rows stack on phones. */}
            <div className={cn(TOPIC_GRID, 'hidden px-5 py-2 text-xs font-medium text-slate-500 sm:grid')} aria-hidden>
              <span>Topic</span>
              <span>Interview evidence</span>
              <span>Market</span>
              <span className="text-right">Signal</span>
            </div>
            <ul className="divide-y divide-slate-100">
              {items.map((item) => (
                <li key={item.topic.id} className={cn(TOPIC_GRID, 'grid gap-x-3 gap-y-2 px-5 py-3 text-sm')}>
                  <div className="flex min-w-0 items-start justify-between gap-2 sm:block">
                    <div className="min-w-0">
                      <p className="font-medium text-slate-900">{item.topic.name}</p>
                      {item.roles.length > 0 && <p className="text-xs text-slate-500">{item.roles.join(', ')}</p>}
                    </div>
                    <span className="shrink-0 sm:hidden">
                      <SignalBadge signal={item.signal} />
                    </span>
                  </div>
                  <div>
                    <div className="flex items-center gap-2">
                      <span className="h-2 w-20 shrink-0 overflow-hidden rounded-full bg-slate-100" aria-hidden>
                        <span className="block h-full rounded-full bg-brand-500" style={{ width: `${(item.interview_records / maxRecords) * 100}%` }} />
                      </span>
                      <span className="text-slate-700 tabular-nums">
                        {item.interview_records} interview record{item.interview_records === 1 ? '' : 's'}
                      </span>
                    </div>
                    <p className="text-xs text-slate-500">
                      {item.approved_questions} approved{item.pending_questions ? ` · ${item.pending_questions} waiting` : ''}
                    </p>
                  </div>
                  <div>
                    {item.research.latest_trend ? (
                      <div className="flex flex-wrap items-center gap-x-2 sm:block">
                        <TrendBadge trend={item.research.latest_trend} />
                        <p className="text-xs text-slate-500 sm:mt-0.5">
                          {item.research.findings} finding{item.research.findings === 1 ? '' : 's'} · {timeAgo(item.research.last_seen).toLowerCase()}
                        </p>
                      </div>
                    ) : (
                      <span className="text-xs text-slate-400">No research yet</span>
                    )}
                  </div>
                  <div className="hidden text-right sm:block">
                    <SignalBadge signal={item.signal} />
                  </div>
                </li>
              ))}
            </ul>
          </Card>
        ))
      )}
    </div>
  )
}

const TABS: { key: Tab; label: string }[] = [
  { key: 'review', label: 'Review queue' },
  { key: 'approved', label: 'Questions' },
  { key: 'topics', label: 'Topics' },
]

export default function IntelligencePage() {
  const [params, setParams] = useSearchParams()
  const tab = (TABS.find((t) => t.key === params.get('tab'))?.key ?? 'review') as Tab
  const summary = useIntelligenceSummary()
  const [open, setOpen] = useState<string | null>(null)
  const s = summary.data

  return (
    <div>
      <PageHeader
        title="Interview intelligence"
        description="What real interviews ask, checked by people, beside what the market wants now."
      />
      <div className="mb-6 grid grid-cols-2 gap-3 lg:grid-cols-4">
        <StatTile label="Waiting for review" value={s ? formatCount(s.pending_questions) : '—'} note="Extracted questions" />
        <StatTile label="Approved questions" value={s ? formatCount(s.approved_questions) : '—'} note={s ? `${s.rejected_questions} rejected` : undefined} />
        <StatTile label="Interview records" value={s ? formatCount(s.interview_records) : '—'} note="With approved questions" />
        <StatTile label="Topics with evidence" value={s ? formatCount(s.topics_with_evidence) : '—'} note={s?.last_exploration_at ? `Last explored ${timeAgo(s.last_exploration_at).toLowerCase()}` : 'Not explored yet'} />
      </div>

      <nav aria-label="Intelligence views" className="mb-5 flex flex-wrap gap-1 rounded-2xl bg-white p-1 shadow-sm ring-1 ring-slate-200/80 sm:w-fit">
        {TABS.map((t) => (
          <button
            key={t.key}
            type="button"
            onClick={() => setParams(t.key === 'review' ? {} : { tab: t.key }, { replace: true })}
            aria-current={tab === t.key ? 'page' : undefined}
            className={cn(
              'rounded-xl px-4 py-2 text-sm font-medium transition',
              tab === t.key ? 'bg-slate-900 text-white' : 'text-slate-600 hover:bg-slate-100',
            )}
          >
            {t.label}
            {t.key === 'review' && s && s.pending_questions > 0 && (
              <span className={cn('ml-1.5 rounded-full px-1.5 text-xs tabular-nums', tab === t.key ? 'bg-white/20' : 'bg-amber-100 text-amber-800')}>
                {s.pending_questions}
              </span>
            )}
          </button>
        ))}
      </nav>

      {tab === 'review' && <ReviewQueue onOpen={setOpen} />}
      {tab === 'approved' && <ApprovedQuestions onOpen={setOpen} />}
      {tab === 'topics' && <TopicsView />}
      {open && <QuestionDialog id={open} onClose={() => setOpen(null)} />}
      {s && s.pending_recommendations > 0 && (
        <p className="mt-6 text-sm text-slate-600">
          {s.pending_recommendations} curriculum recommendation{s.pending_recommendations === 1 ? '' : 's'} from market research{' '}
          {s.pending_recommendations === 1 ? 'is' : 'are'} waiting for a decision in{' '}
          <Link to="/admin/agents/research" className="font-semibold text-brand-700 hover:underline">
            Market research
          </Link>
          .
        </p>
      )}
    </div>
  )
}

