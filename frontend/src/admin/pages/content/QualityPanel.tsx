import { useQueryClient } from '@tanstack/react-query'
import { AlertTriangle, Bot, CircleCheck, CircleX, Star } from 'lucide-react'
import { useEffect, useState, type ReactNode } from 'react'

import { Button } from '../../../components/ui/Button'
import { Alert, Badge, Skeleton } from '../../../components/ui/Feedback'
import { SelectField, TextAreaField } from '../../../components/ui/Field'
import { useToast } from '../../../components/ui/Toast'
import { errorMessage } from '../../../lib/api'
import { cn } from '../../../lib/cn'
import { formatDateTime, timeAgo } from '../../../lib/format'
import { adminKeys } from '../../../lib/queryClient'
import type { AiReview, AutomatedCheck, CheckStatus, RatingSummary, ReviewIssue, VersionDetail } from '../../../lib/types'
import { useCan } from '../../api'
import { useContentJob, useRateVersion, useStartAiReview, useVersionQuality } from '../../contentApi'

const STATUS_ICON: Record<CheckStatus, { icon: typeof CircleCheck; tone: string; label: string }> = {
  passed: { icon: CircleCheck, tone: 'text-emerald-600', label: 'Passed' },
  warning: { icon: AlertTriangle, tone: 'text-amber-600', label: 'Warning' },
  error: { icon: CircleX, tone: 'text-rose-600', label: 'Error' },
}

const SCORE_LABELS: Record<string, string> = {
  factual_correctness: 'Factual correctness',
  clarity: 'Clarity',
  math_consistency: 'Maths consistency',
  topic_relevance: 'Topic relevance',
  interview_relevance: 'Interview relevance',
  difficulty_fit: 'Difficulty labels',
  engagement: 'Engagement',
  tasks_doable: 'Tasks doable with the controls',
  code_quality: 'Code quality',
  answer_quality: 'Answer quality',
  assessment_quality: 'Assessment quality',
  revision_usefulness: 'Revision usefulness',
  script_quality: 'Script quality',
}

// The database doesn't keep key order, so scores are shown in this fixed order.
const SCORE_ORDER = Object.keys(SCORE_LABELS)

const SEVERITY: Record<ReviewIssue['severity'], { label: string; tone: 'danger' | 'warning' | 'neutral' }> = {
  error: { label: 'Error', tone: 'danger' },
  warning: { label: 'Warning', tone: 'warning' },
  suggestion: { label: 'Suggestion', tone: 'neutral' },
}

const letter = (index: number | null) => (index === null ? '—' : String.fromCharCode(65 + index))

function Section({ title, description, action, children }: { title: string; description: string; action?: ReactNode; children: ReactNode }) {
  return (
    <section className="space-y-3">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h3 className="font-semibold text-slate-900">{title}</h3>
          <p className="text-sm text-slate-500">{description}</p>
        </div>
        {action}
      </div>
      {children}
    </section>
  )
}

function CheckRow({ check }: { check: AutomatedCheck }) {
  const { icon: Icon, tone, label } = STATUS_ICON[check.status]
  return (
    <li className="py-2.5">
      <div className="flex items-start gap-2.5">
        <Icon className={cn('mt-0.5 size-4 shrink-0', tone)} aria-label={label} />
        <div className="min-w-0 flex-1">
          <p className="text-sm font-medium text-slate-900">{check.label}</p>
          {check.note && <p className="text-xs text-slate-500">{check.note}</p>}
          {check.findings.length > 0 && (
            <ul className="mt-1 space-y-1">
              {check.findings.map((finding, i) => (
                <li key={i} className="text-sm text-slate-700">
                  {finding.where && <span className="mr-1.5 rounded bg-slate-100 px-1.5 py-0.5 font-mono text-xs text-slate-600">{finding.where}</span>}
                  {finding.message}
                </li>
              ))}
            </ul>
          )}
        </div>
      </div>
    </li>
  )
}

function ScoreBar({ label, score }: { label: string; score: number | null }) {
  return (
    <li className="flex items-center gap-3 text-sm">
      <span className="w-48 shrink-0 text-slate-700">{label}</span>
      {score === null ? (
        <span className="text-xs text-slate-400">Not applicable</span>
      ) : (
        <>
          <span className="flex flex-1 gap-1" role="img" aria-label={`${label}: ${score} out of 5`}>
            {[1, 2, 3, 4, 5].map((n) => (
              <span key={n} className={cn('h-2 flex-1 rounded-full', n <= score ? 'bg-brand-600' : 'bg-slate-200')} />
            ))}
          </span>
          <span className="w-8 text-right font-semibold text-slate-700 tabular-nums">{score}/5</span>
        </>
      )}
    </li>
  )
}

function ReviewReport({ review, quizOptions }: { review: AiReview; quizOptions: string[][] | null }) {
  const disagreements = review.quiz_check?.filter((row) => !row.agrees) ?? []
  return (
    <div className="space-y-4 rounded-2xl bg-slate-50 p-4 ring-1 ring-slate-200">
      <div className="flex flex-wrap items-center gap-2 text-xs text-slate-500">
        <Badge tone="brand">Average {review.average?.toFixed(1) ?? '—'} / 5</Badge>
        <span>
          {review.model} · {formatDateTime(review.created_at)}
          {review.requested_by ? ` · asked by ${review.requested_by}` : ''}
        </span>
      </div>
      <p className="text-sm text-slate-800">{review.summary}</p>
      <ul className="space-y-2">
        {Object.entries(review.scores)
          .sort(([a], [b]) => SCORE_ORDER.indexOf(a) - SCORE_ORDER.indexOf(b))
          .map(([key, score]) => (
            <ScoreBar key={key} label={SCORE_LABELS[key] ?? key} score={score} />
          ))}
      </ul>

      {review.quiz_check && (
        <div>
          <p className="text-sm font-semibold text-slate-900">
            Answer key check: the reviewer solved the quiz without the key
            {disagreements.length === 0 ? ' and agreed on every question.' : ` and disagreed on ${disagreements.length}.`}
          </p>
          {disagreements.length > 0 && (
            <ul className="mt-2 space-y-1 text-sm">
              {disagreements.map((row) => (
                <li key={row.question} className="rounded-xl bg-rose-50 px-3 py-2 text-rose-900 ring-1 ring-rose-100">
                  Question {row.question}: the key says <strong>{letter(row.key)}</strong>
                  {quizOptions?.[row.question - 1]?.[row.key] ? ` (${quizOptions[row.question - 1][row.key]})` : ''}, the reviewer picked{' '}
                  <strong>{letter(row.picked)}</strong>
                  {row.picked !== null && quizOptions?.[row.question - 1]?.[row.picked] ? ` (${quizOptions[row.question - 1][row.picked]})` : ''}
                  {row.confident ? '' : ', unsure'}. Check the key and that only one option is right.
                </li>
              ))}
            </ul>
          )}
        </div>
      )}

      {review.issues.length === 0 ? (
        <p className="text-sm text-slate-600">No issues reported.</p>
      ) : (
        <ul className="space-y-3">
          {review.issues.map((issue, i) => (
            <li key={i} className="rounded-xl bg-white p-3 ring-1 ring-slate-200">
              <div className="flex flex-wrap items-center gap-2">
                <Badge tone={SEVERITY[issue.severity].tone}>{SEVERITY[issue.severity].label}</Badge>
                <span className="text-xs font-medium text-slate-500">{issue.location}</span>
              </div>
              {issue.quote && <p className="mt-1.5 border-l-2 border-slate-300 pl-2 text-sm text-slate-600 italic">&ldquo;{issue.quote}&rdquo;</p>}
              <p className="mt-1.5 text-sm text-slate-900">{issue.problem}</p>
              <p className="mt-1 text-sm text-slate-600">
                <span className="font-medium">Fix:</span> {issue.fix}
              </p>
            </li>
          ))}
        </ul>
      )}
      {review.dropped_issues > 0 && (
        <p className="text-xs text-slate-500">
          {review.dropped_issues} issue(s) were dropped because they quoted text that isn&apos;t in this version.
        </p>
      )}
    </div>
  )
}

function AiReviewSection({ version, reviews, reviewModel, aiConfigured }: { version: VersionDetail; reviews: AiReview[]; reviewModel: string; aiConfigured: boolean }) {
  const canReview = useCan('content.review', 'content.publish')
  const start = useStartAiReview()
  const toast = useToast()
  const queryClient = useQueryClient()
  const [limit, setLimit] = useState('0.5')
  const [jobId, setJobId] = useState<string | null>(null)
  const job = useContentJob(jobId ?? '', !!jobId)
  const running = !!jobId && (!job.data || job.data.status === 'queued' || job.data.status === 'running')

  useEffect(() => {
    if (jobId && job.data && !running) {
      queryClient.invalidateQueries({ queryKey: adminKeys.contentQuality(version.id) })
      if (job.data.error) toast.error(job.data.error)
      setJobId(null)
    }
  }, [jobId, job.data, running, queryClient, version.id, toast])

  const quizOptions = version.component === 'quiz' ? (version.body as { questions: { options: string[] }[] }).questions.map((q) => q.options) : null
  return (
    <Section
      title="AI review"
      description={`A second AI model (${reviewModel}) scores this version and lists problems. It's advice, not verification.`}
      action={
        canReview && (
          <div className="flex items-end gap-2">
            <SelectField label="Spending limit" value={limit} onChange={(e) => setLimit(e.target.value)} className="w-32">
              <option value="0.25">$0.25</option>
              <option value="0.5">$0.50</option>
              <option value="1">$1.00</option>
            </SelectField>
            <Button
              icon={<Bot className="size-4" />}
              disabled={!aiConfigured}
              loading={start.isPending || running}
              onClick={() =>
                start.mutate(
                  { versionId: version.id, max_cost_usd: limit },
                  { onSuccess: (started) => setJobId(started.id), onError: (e) => toast.error(errorMessage(e)) },
                )
              }
            >
              {running ? 'Reviewing…' : reviews.length ? 'Review again' : 'Run AI review'}
            </Button>
          </div>
        )
      }
    >
      {!aiConfigured && <Alert tone="info">AI reviews need the OpenRouter key. The automated checks above work without it.</Alert>}
      {reviews.length === 0 ? (
        <p className="text-sm text-slate-500">{running ? 'The reviewer is reading this version…' : 'No AI review of this version yet.'}</p>
      ) : (
        <>
          <ReviewReport review={reviews[0]} quizOptions={quizOptions} />
          {reviews.length > 1 && <p className="text-xs text-slate-500">{reviews.length - 1} earlier review(s) of this version are kept.</p>}
        </>
      )}
    </Section>
  )
}

function RatingSection({ versionId, ratings }: { versionId: string; ratings: RatingSummary }) {
  const canRate = useCan('content.review', 'content.publish')
  const rate = useRateVersion(versionId)
  const toast = useToast()
  const mine = ratings.ratings.find((r) => r.mine)
  const [scores, setScores] = useState<Record<string, number>>(mine?.scores ?? {})
  const [note, setNote] = useState(mine?.note ?? '')
  const complete = ratings.criteria.every((c) => scores[c.key])

  return (
    <Section
      title="Reviewer rating"
      description="Your judgement on the pilot rubric, 1 (poor) to 5 (excellent). It feeds the pilot evaluation before content expands."
      action={ratings.average !== null && <Badge tone="brand">Average {ratings.average.toFixed(1)} / 5 from {ratings.ratings.length}</Badge>}
    >
      {canRate && (
        <form
          className="space-y-3 rounded-2xl bg-slate-50 p-4 ring-1 ring-slate-200"
          onSubmit={(event) => {
            event.preventDefault()
            rate.mutate(
              { scores, note: note.trim() || undefined },
              { onSuccess: () => toast.success('Rating saved'), onError: (e) => toast.error(errorMessage(e)) },
            )
          }}
        >
          {ratings.criteria.map((criterion) => (
            <fieldset key={criterion.key} className="flex flex-wrap items-center justify-between gap-2">
              <legend className="float-left text-sm text-slate-700">{criterion.label}</legend>
              <div className="flex gap-1">
                {[1, 2, 3, 4, 5].map((n) => (
                  <label key={n} className="cursor-pointer">
                    <input
                      type="radio"
                      name={criterion.key}
                      value={n}
                      checked={scores[criterion.key] === n}
                      onChange={() => setScores({ ...scores, [criterion.key]: n })}
                      className="peer sr-only"
                    />
                    <span className="flex size-8 items-center justify-center rounded-lg bg-white text-sm font-semibold text-slate-600 ring-1 ring-slate-200 peer-checked:bg-brand-600 peer-checked:text-white peer-checked:ring-brand-600 peer-focus-visible:ring-2 peer-focus-visible:ring-brand-500">
                      {n}
                    </span>
                  </label>
                ))}
              </div>
            </fieldset>
          ))}
          <TextAreaField label="Note (optional)" rows={2} maxLength={1000} value={note} onChange={(e) => setNote(e.target.value)} />
          <Button type="submit" size="sm" icon={<Star className="size-4" />} disabled={!complete} loading={rate.isPending}>
            {mine ? 'Update my rating' : 'Save my rating'}
          </Button>
        </form>
      )}
      {ratings.ratings.filter((r) => !r.mine || !canRate).length > 0 && (
        <ul className="divide-y divide-slate-100 text-sm">
          {ratings.ratings
            .filter((r) => !r.mine || !canRate)
            .map((r) => (
              <li key={r.admin} className="py-2">
                <span className="font-medium text-slate-900">{r.admin}</span>
                <span className="text-slate-500"> · {r.average.toFixed(1)} / 5 · {timeAgo(r.created_at)}</span>
                {r.note && <p className="text-slate-600">{r.note}</p>}
              </li>
            ))}
        </ul>
      )}
      {ratings.ratings.length === 0 && !canRate && <p className="text-sm text-slate-500">Nobody has rated this version yet.</p>}
    </Section>
  )
}

/** Automated checks, the AI review and reviewer ratings for one version. */
export function QualityPanel({ version }: { version: VersionDetail }) {
  const quality = useVersionQuality(version.id)
  if (quality.isPending) return <Skeleton className="h-64" />
  if (quality.isError) return <Alert>{errorMessage(quality.error)}</Alert>
  const { automated, ai_reviews, ratings, review_model, ai_configured } = quality.data
  return (
    <div className="space-y-8">
      <Section
        title="Automated checks"
        description="Free checks run in code every time you open this. Errors block publishing; warnings are for you to judge."
        action={
          <Badge tone={automated.errors ? 'danger' : automated.warnings ? 'warning' : 'success'}>
            {automated.errors ? `${automated.errors} error(s)` : automated.warnings ? `${automated.warnings} warning(s)` : 'All passed'}
          </Badge>
        }
      >
        <ul className="divide-y divide-slate-100">
          {automated.checks.map((check) => (
            <CheckRow key={check.key} check={check} />
          ))}
        </ul>
      </Section>
      <AiReviewSection version={version} reviews={ai_reviews} reviewModel={review_model} aiConfigured={ai_configured} />
      <RatingSection key={version.id} versionId={version.id} ratings={ratings} />
    </div>
  )
}
