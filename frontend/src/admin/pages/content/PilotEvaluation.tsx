import { Bot, ChevronDown, CircleCheck, CircleX, Star } from 'lucide-react'
import { useState } from 'react'
import { Link } from 'react-router'

import { StatTile } from '../../../components/ui/StatTile'
import { Alert, Card, CardHeader, Skeleton } from '../../../components/ui/Feedback'
import { SECTION_ORDER, SECTIONS } from '../../../learn/sections'
import { errorMessage } from '../../../lib/api'
import { cn } from '../../../lib/cn'
import { formatUsd } from '../../../lib/format'
import type { PilotComponent, PilotEvaluation, TopicInsights } from '../../../lib/types'
import { usePilotEvaluation, useTopicInsights } from '../../contentApi'
import { VERSION_STATUS } from './shared'

const fmt = (value: number | null) => (value === null ? '—' : value.toFixed(1))

/** One-line summary of the pilot, for the expansion decision. */
export function pilotSummary(evaluation: PilotEvaluation): string {
  const { totals } = evaluation
  return [
    `${totals.published} of ${totals.components} components published`,
    `${totals.with_errors} with check errors`,
    `${totals.ai_reviewed} AI-reviewed${totals.average_ai_score !== null ? ` (avg ${fmt(totals.average_ai_score)}/5)` : ''}`,
    `${totals.rated} rated by reviewers${totals.average_rating !== null ? ` (avg ${fmt(totals.average_rating)}/5)` : ''}`,
  ].join(' · ')
}

function Cell({ topicId, cell }: { topicId: string; cell: PilotComponent }) {
  const status = cell.published_number !== null ? 'published' : cell.latest_status
  const meta = status ? VERSION_STATUS[status] : null
  return (
    <Link
      to={`/admin/content/${topicId}?c=${cell.component}`}
      className="block rounded-xl px-2 py-1.5 text-xs transition hover:bg-slate-100"
      aria-label={`${SECTIONS[cell.component].admin}: ${meta?.label ?? 'no content'}${cell.errors ? `, ${cell.errors} check errors` : ''}`}
    >
      <span className="flex items-center gap-1.5 font-medium text-slate-800">
        <span className={cn('size-1.5 rounded-full', meta?.dot ?? 'bg-slate-200')} aria-hidden />
        {cell.published_number !== null ? `v${cell.published_number} live` : cell.latest_number ? `v${cell.latest_number} ${meta?.label.toLowerCase()}` : 'None'}
      </span>
      <span className="mt-0.5 flex flex-wrap gap-x-2 text-slate-500">
        {cell.errors > 0 ? (
          <span className="inline-flex items-center gap-0.5 font-semibold text-rose-700">
            <CircleX className="size-3" aria-hidden /> {cell.errors}
          </span>
        ) : (
          cell.latest_number !== null && <CircleCheck className="size-3 text-emerald-600" aria-hidden />
        )}
        {cell.ai_score !== null && (
          <span className="inline-flex items-center gap-0.5" title="AI review average">
            <Bot className="size-3" aria-hidden /> {fmt(cell.ai_score)}
          </span>
        )}
        {cell.rating !== null && (
          <span className="inline-flex items-center gap-0.5" title={`Reviewer average from ${cell.ratings}`}>
            <Star className="size-3" aria-hidden /> {fmt(cell.rating)}
          </span>
        )}
      </span>
    </Link>
  )
}

function PilotTable({ evaluation }: { evaluation: PilotEvaluation }) {
  return (
    <>
      <p className="border-t border-slate-100 px-5 pt-3 text-xs text-slate-500">Each cell shows what students see, or the latest draft if nothing is live. Click one to open it.</p>
      <div className="overflow-x-auto">
        <table className="w-full min-w-[56rem] text-left">
          <thead className="bg-slate-50 text-xs font-medium text-slate-500">
            <tr>
              <th scope="col" className="px-5 py-2">
                Topic
              </th>
              {SECTION_ORDER.map((component) => (
                <th key={component} scope="col" className="px-2 py-2">
                  {SECTIONS[component].label}
                </th>
              ))}
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100">
            {evaluation.topics.map(({ topic, components }) => (
              <tr key={topic.id}>
                <th scope="row" className="px-5 py-2 text-sm font-medium text-slate-900">
                  <Link to={`/admin/content/${topic.id}`} className="hover:text-brand-700">
                    {topic.name}
                  </Link>
                </th>
                {SECTION_ORDER.map((component) => {
                  const cell = components.find((c) => c.component === component)
                  return (
                    <td key={component} className="px-1 py-1 align-top">
                      {cell ? <Cell topicId={topic.id} cell={cell} /> : <span className="px-2 text-xs text-slate-400">No widget</span>}
                    </td>
                  )
                })}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <p className="flex flex-wrap gap-x-4 gap-y-1 border-t border-slate-100 px-5 py-3 text-xs text-slate-500">
        <span className="inline-flex items-center gap-1">
          <CircleX className="size-3 text-rose-700" aria-hidden /> automated check errors
        </span>
        <span className="inline-flex items-center gap-1">
          <Bot className="size-3" aria-hidden /> AI review average (1–5)
        </span>
        <span className="inline-flex items-center gap-1">
          <Star className="size-3" aria-hidden /> reviewer rating average (1–5)
        </span>
      </p>
    </>
  )
}

/** Everything to judge before the green signal to expand beyond the pilot. */
export function PilotEvaluationCard() {
  const evaluation = usePilotEvaluation()
  const [details, setDetails] = useState(false)
  return (
    <Card className="overflow-hidden">
      <CardHeader
        title="Pilot evaluation"
        description="For your decision on expanding beyond the pilot: what's published, what the automated checks found, AI review scores and your reviewers' ratings."
        action={
          <button
            type="button"
            aria-expanded={details}
            onClick={() => setDetails(!details)}
            className="inline-flex items-center gap-1 rounded-lg px-2.5 py-1.5 text-sm font-semibold text-slate-700 hover:bg-slate-100"
          >
            {details ? 'Hide' : 'Show'} topic details
            <ChevronDown className={cn('size-4 transition', details && 'rotate-180')} aria-hidden />
          </button>
        }
      />
      {evaluation.isPending ? (
        <Skeleton className="m-5 h-40" />
      ) : evaluation.isError ? (
        <Alert className="m-5">{errorMessage(evaluation.error)}</Alert>
      ) : (
        <>
          <div className="grid grid-cols-2 gap-3 p-5 lg:grid-cols-4">
            <StatTile label="Published" value={`${evaluation.data.totals.published} / ${evaluation.data.totals.components}`} />
            <StatTile label="With check errors" value={String(evaluation.data.totals.with_errors)} note="Errors block publishing" />
            <StatTile
              label="AI-reviewed"
              value={String(evaluation.data.totals.ai_reviewed)}
              note={evaluation.data.totals.average_ai_score !== null ? `Average ${fmt(evaluation.data.totals.average_ai_score)} / 5` : 'None yet'}
            />
            <StatTile
              label="Rated by reviewers"
              value={String(evaluation.data.totals.rated)}
              note={evaluation.data.totals.average_rating !== null ? `Average ${fmt(evaluation.data.totals.average_rating)} / 5` : 'None yet'}
            />
          </div>
          {details && <PilotTable evaluation={evaluation.data} />}
        </>
      )}
    </Card>
  )
}

function Coverage({ insights }: { insights: TopicInsights }) {
  const questions = [...insights.actual_questions.map((q) => ({ ...q, kind: 'Real interview' })), ...insights.research_questions.map((q) => ({ ...q, kind: 'Research' }))]
  if (questions.length === 0) {
    return (
      <p className="text-sm text-slate-600">
        No approved interview questions for this topic yet. Once interview records are reviewed in Interview intelligence, this shows which ones the
        interview prep uses.
      </p>
    )
  }
  const used = questions.filter((q) => q.used).length
  return (
    <div className="space-y-2">
      <p className="text-sm text-slate-700">
        {used} of {questions.length} approved question(s) are used in interview prep
        {insights.interview_version !== null && ` v${insights.interview_version}${insights.interview_published ? ' (live)' : ' (latest draft)'}`}.
        {used < questions.length && ' Generate or revise the interview prep with intelligence on to include the rest.'}
      </p>
      <ul className="divide-y divide-slate-100 text-sm">
        {questions.map((q) => (
          <li key={q.id} className="flex items-start gap-2 py-2">
            {q.used ? (
              <CircleCheck className="mt-0.5 size-4 shrink-0 text-emerald-600" aria-label="Used" />
            ) : (
              <CircleX className="mt-0.5 size-4 shrink-0 text-slate-400" aria-label="Not used yet" />
            )}
            <span className="min-w-0 flex-1 text-slate-800">{q.question}</span>
            <span className="shrink-0 text-xs text-slate-500">
              {q.kind}
              {q.role ? ` · ${q.role}` : ''}
            </span>
          </li>
        ))}
      </ul>
    </div>
  )
}

/** AI spend on a topic and which approved interview questions its interview prep covers. */
export function TopicInsightsCard({ topicId }: { topicId: string }) {
  const insights = useTopicInsights(topicId)
  return (
    <Card className="overflow-hidden">
      <CardHeader
        title="Interview coverage & spend"
        description={insights.data ? `AI spend on this topic: ${formatUsd(insights.data.spend_usd)} across ${insights.data.runs} run(s).` : 'AI spend and interview coverage for this topic.'}
      />
      <div className="p-5">
        {insights.isPending ? <Skeleton className="h-16" /> : insights.isError ? <Alert>{errorMessage(insights.error)}</Alert> : <Coverage insights={insights.data} />}
      </div>
    </Card>
  )
}
