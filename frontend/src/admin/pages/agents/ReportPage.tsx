import { ArrowLeft, Check, CircleCheck, ExternalLink, TriangleAlert, X } from 'lucide-react'
import { useMemo } from 'react'
import { Link, useParams } from 'react-router'

import { Button } from '../../../components/ui/Button'
import { Alert, Badge, Card, CardHeader, Skeleton } from '../../../components/ui/Feedback'
import { useToast } from '../../../components/ui/Toast'
import { errorMessage } from '../../../lib/api'
import { formatDate, formatDateTime } from '../../../lib/format'
import type { ReportDetail } from '../../../lib/types'
import { useCan } from '../../api'
import { useReport, useReviewResearchQuestion } from '../../intelApi'
import { ReviewBadge } from '../intelligence/shared'
import { RecommendationCard } from './RecommendationCard'
import { TrendBadge } from './shared'

function Findings({ report }: { report: ReportDetail }) {
  const sources = useMemo(
    () => new Map(report.source_list.map((s, index) => [s.id, { ...s, number: index + 1 }])),
    [report.source_list],
  )
  return (
    <Card>
      <CardHeader title="Findings" description="Each one cites the sources it rests on. Uncited claims were dropped." />
      <ol className="divide-y divide-slate-100">
        {report.finding_list.map((finding, index) => (
          <li key={finding.id} className="px-5 py-4">
            <div className="flex flex-wrap items-center gap-2">
              <span className="text-xs font-semibold text-slate-400 tabular-nums">{index + 1}</span>
              <p className="font-medium text-slate-900">{finding.topic_label}</p>
              <TrendBadge trend={finding.trend} />
              {finding.topic && <Badge tone="brand">{finding.topic.name}</Badge>}
            </div>
            <p className="mt-1 text-sm text-slate-700">{finding.observation}</p>
            {(finding.roles.length > 0 || finding.skills.length > 0) && (
              <p className="mt-1 text-xs text-slate-500">{[...finding.roles, ...finding.skills].join(' · ')}</p>
            )}
            <ul className="mt-2 space-y-1.5">
              {finding.evidence.map((ev, i) => {
                const source = sources.get(ev.source_id)
                return (
                  <li key={i} className="flex gap-2 text-xs text-slate-600">
                    {ev.quote ? (
                      ev.quote_verified ? (
                        <CircleCheck className="mt-0.5 size-3.5 shrink-0 text-emerald-600" aria-label="Quote found in the source" />
                      ) : (
                        <TriangleAlert className="mt-0.5 size-3.5 shrink-0 text-amber-500" aria-label="Quote not found in the search excerpt" />
                      )
                    ) : (
                      <span className="size-3.5 shrink-0" />
                    )}
                    <span className="min-w-0">
                      {ev.quote && <q className="italic">{ev.quote}</q>}{' '}
                      {source && (
                        <a href={source.url} target="_blank" rel="noreferrer noopener" className="font-semibold text-brand-700 hover:underline">
                          [{source.number}] {source.site}
                        </a>
                      )}
                      {ev.quote && !ev.quote_verified && (
                        <span className="text-amber-700"> · not found in the search excerpt; check the page</span>
                      )}
                    </span>
                  </li>
                )
              })}
            </ul>
          </li>
        ))}
      </ol>
    </Card>
  )
}

function PracticeQuestions({ report }: { report: ReportDetail }) {
  const canReview = useCan('intelligence.review')
  const review = useReviewResearchQuestion()
  const toast = useToast()
  if (!report.question_list.length) return null
  return (
    <Card>
      <CardHeader
        title="Research-derived practice questions"
        description="Suggested from what employers ask for. These are not real interview questions and are kept separate."
      />
      <ul className="divide-y divide-slate-100">
        {report.question_list.map((q) => (
          <li key={q.id} className="flex flex-wrap items-start gap-3 px-5 py-3">
            <div className="min-w-0 flex-1">
              <p className="text-sm text-slate-900">{q.text}</p>
              <p className="mt-0.5 text-xs text-slate-500">
                {[q.topic?.name ?? q.topic_label, q.role].filter(Boolean).join(' · ')} — {q.rationale}
              </p>
            </div>
            <ReviewBadge status={q.status} />
            {canReview && q.status === 'pending_review' && (
              <span className="flex gap-1">
                <Button
                  variant="ghost"
                  size="sm"
                  icon={<X className="size-3.5" />}
                  onClick={() => review.mutate({ id: q.id, status: 'rejected' }, { onError: (e) => toast.error(errorMessage(e)) })}
                >
                  Reject
                </Button>
                <Button
                  variant="secondary"
                  size="sm"
                  icon={<Check className="size-3.5" />}
                  onClick={() => review.mutate({ id: q.id, status: 'approved' }, { onError: (e) => toast.error(errorMessage(e)) })}
                >
                  Approve
                </Button>
              </span>
            )}
          </li>
        ))}
      </ul>
    </Card>
  )
}

export default function ReportPage() {
  const { id = '' } = useParams()
  const report = useReport(id)

  return (
    <div>
      <Link
        to="/admin/agents/research"
        className="mb-5 inline-flex items-center gap-1.5 text-sm font-medium text-slate-600 hover:text-slate-900"
      >
        <ArrowLeft className="size-4" aria-hidden /> Market research
      </Link>
      {report.isPending ? (
        <Skeleton className="h-64 rounded-2xl" />
      ) : report.isError ? (
        <Alert>{errorMessage(report.error)}</Alert>
      ) : (
        <div className="space-y-5">
          <div>
            <h1 className="font-display text-2xl font-bold tracking-tight text-slate-900 sm:text-3xl">{report.data.title}</h1>
            <p className="mt-1 text-sm text-slate-500">
              {formatDateTime(report.data.created_at)}
              {report.data.triggered_by && ` · requested by ${report.data.triggered_by}`} · {report.data.model}
            </p>
            <div className="mt-2 flex flex-wrap gap-1">
              {report.data.scope.roles.map((r) => (
                <Badge key={r}>{r}</Badge>
              ))}
              <Badge>{report.data.scope.region}</Badge>
              <Badge>Last {report.data.scope.months} months</Badge>
              {report.data.scope.focus && <Badge tone="brand">Focus: {report.data.scope.focus}</Badge>}
            </div>
          </div>

          <Card className="p-5">
            <h2 className="mb-1 font-display text-base font-semibold text-slate-900">Summary</h2>
            <p className="text-sm leading-relaxed text-slate-700">{report.data.summary}</p>
            <p className="mt-2 text-xs text-slate-500">Written by AI from the cited sources below. Check the findings before acting on it.</p>
          </Card>

          <div className="grid gap-5 lg:grid-cols-[minmax(0,1fr)_380px]">
            <div className="min-w-0 space-y-5">
              <Findings report={report.data} />
              <PracticeQuestions report={report.data} />
            </div>
            <div className="space-y-5">
              <Card>
                <CardHeader title="Recommendations" />
                <div className="space-y-3 p-5">
                  {report.data.recommendations.length === 0 ? (
                    <p className="text-sm text-slate-500">No recommendations backed by findings.</p>
                  ) : (
                    report.data.recommendations.map((rec) => <RecommendationCard key={rec.id} rec={rec} showReport={false} />)
                  )}
                </div>
              </Card>
              <Card>
                <CardHeader title="Sources" description={`Read ${formatDate(report.data.created_at)}`} />
                <ol className="divide-y divide-slate-100">
                  {report.data.source_list.map((source, index) => (
                    <li key={source.id} className="px-5 py-3">
                      <a
                        href={source.url}
                        target="_blank"
                        rel="noreferrer noopener"
                        className="inline-flex items-start gap-1 text-sm font-medium text-slate-900 hover:text-brand-700"
                      >
                        <span className="text-slate-400 tabular-nums">[{index + 1}]</span> {source.title}
                        <ExternalLink className="mt-0.5 size-3.5 shrink-0" aria-hidden />
                      </a>
                      <p className="text-xs text-slate-500">{source.site}</p>
                      {source.excerpt && (
                        <details className="mt-1">
                          <summary className="cursor-pointer text-xs font-medium text-brand-700">Excerpt</summary>
                          <p className="mt-1 max-h-40 overflow-y-auto text-xs whitespace-pre-wrap text-slate-600">{source.excerpt}</p>
                        </details>
                      )}
                    </li>
                  ))}
                </ol>
              </Card>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
