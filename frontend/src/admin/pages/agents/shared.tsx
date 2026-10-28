import {
  ArrowUpRight,
  CircleAlert,
  Info,
  Minus,
  RotateCcw,
  Sprout,
  Square,
  TrendingDown,
  TrendingUp,
  TriangleAlert,
  type LucideIcon,
} from 'lucide-react'
import { Link } from 'react-router'

import { Button } from '../../../components/ui/Button'
import { Dialog } from '../../../components/ui/Dialog'
import { Alert, Badge, Skeleton } from '../../../components/ui/Feedback'
import { useToast } from '../../../components/ui/Toast'
import { errorMessage } from '../../../lib/api'
import { formatDateTime, formatUsd } from '../../../lib/format'
import type { AgentJob, AgentStatus, ContentJobDetail, JobKind, TopicSignal, Trend } from '../../../lib/types'
import { useCan } from '../../api'
import { useContentJob, useStopContentJob } from '../../contentApi'
import { useAgentJob, useRetryAgentJob, useStopAgentJob } from '../../intelApi'
import { duration, isActive, JobStatusBadge } from '../sources/shared'

export const KIND_LABELS: Record<JobKind, string> = {
  source_fetch: 'Source fetch',
  source_import: 'File import',
  exploration: 'Exploration agent',
  market_research: 'Market research',
  content_generation: 'Content generation',
  content_narration: 'Narration',
}

const CONTENT_KINDS: JobKind[] = ['content_generation', 'content_narration']

/** Labels for the counters each kind of run reports, in display order. */
const RESULT_LABELS: Record<JobKind, [string, string][]> = {
  source_fetch: [
    ['new', 'New'],
    ['updated', 'Updated'],
    ['unchanged', 'Unchanged'],
    ['skipped_known', 'Already fetched'],
  ],
  source_import: [
    ['new', 'New'],
    ['updated', 'Updated'],
    ['unchanged', 'Unchanged'],
  ],
  exploration: [
    ['records_read', 'Records read'],
    ['interview_records', 'Interviews found'],
    ['questions', 'Questions extracted'],
    ['not_word_for_word', 'Not word-for-word'],
    ['possible_duplicates', 'Possible duplicates'],
    ['not_interview', 'Not interviews'],
    ['failed', "Couldn't read"],
    ['records_left', 'Left for next run'],
    ['fetched_new', 'Newly fetched'],
  ],
  market_research: [
    ['sources', 'Sources'],
    ['findings', 'Cited findings'],
    ['findings_dropped', 'Uncited, dropped'],
    ['unverified_quotes', 'Unverified quotes'],
    ['recommendations', 'Recommendations'],
    ['questions', 'Practice questions'],
  ],
  content_generation: [
    ['generated', 'Drafts generated'],
    ['failed', 'Failed'],
  ],
  content_narration: [['scenes_narrated', 'Scenes narrated']],
}

export function resultCounts(job: Pick<AgentJob, 'kind' | 'result'>): { label: string; value: number }[] {
  return RESULT_LABELS[job.kind]
    .map(([key, label]) => ({ label, value: Number(job.result[key] ?? 0) }))
    .filter((item, index) => index < 3 || item.value > 0)
}

export function runHeadline(job: AgentJob): string {
  if (job.error) return job.error
  if (job.kind === 'exploration') {
    if (isActive(job)) {
      return job.progress_total
        ? `Reading ${job.progress_done} of ${job.progress_total} records`
        : 'Starting'
    }
    return `${job.result.questions ?? 0} questions from ${job.result.interview_records ?? 0} interviews`
  }
  if (job.kind === 'market_research') {
    if (isActive(job)) return 'Searching and writing the report'
    return `${job.result.findings ?? 0} cited findings, ${job.result.recommendations ?? 0} recommendations`
  }
  if (job.kind === 'content_generation') {
    if (isActive(job)) {
      return job.progress_total ? `Writing component ${Math.min(job.progress_done + 1, job.progress_total)} of ${job.progress_total}` : 'Starting'
    }
    const failed = Number(job.result.failed ?? 0)
    return `${job.result.generated ?? 0} draft(s) ready for review${failed ? `, ${failed} failed` : ''}`
  }
  if (job.kind === 'content_narration') {
    if (isActive(job)) return job.progress_total ? `Narrating ${job.progress_done} of ${job.progress_total} scenes` : 'Starting'
    return `${job.result.scenes_narrated ?? 0} scene(s) narrated`
  }
  return resultCounts(job)
    .filter((c) => c.value)
    .map((c) => `${c.value} ${c.label.toLowerCase()}`)
    .join(' · ') || 'No records'
}

export function AiStatusBanner({ status }: { status: AgentStatus | undefined }) {
  if (!status || status.ai_configured) return null
  return (
    <Alert tone="info" className="mb-5">
      The AI provider isn&apos;t connected yet, so agents can&apos;t run. Add{' '}
      <code className="rounded bg-white/70 px-1 text-xs">IPP_OPENROUTER_API_KEY</code> to{' '}
      <code className="text-xs">backend/.env</code> and restart the API. Everything already collected
      stays viewable.
    </Alert>
  )
}

const TRENDS: Record<Trend, { label: string; tone: 'success' | 'brand' | 'neutral' | 'warning'; icon: LucideIcon }> = {
  emerging: { label: 'Emerging', tone: 'brand', icon: Sprout },
  rising: { label: 'Rising', tone: 'success', icon: TrendingUp },
  stable: { label: 'Stable', tone: 'neutral', icon: Minus },
  declining: { label: 'Declining', tone: 'warning', icon: TrendingDown },
  unclear: { label: 'Unclear', tone: 'neutral', icon: Minus },
}

export function TrendBadge({ trend }: { trend: Trend }) {
  const { label, tone, icon: Icon } = TRENDS[trend]
  return (
    <Badge tone={tone}>
      <Icon className="size-3" aria-hidden /> {label}
    </Badge>
  )
}

export const SIGNALS: Record<TopicSignal, { label: string; tone: 'success' | 'brand' | 'neutral' | 'warning'; help: string }> = {
  asked_and_rising: {
    label: 'Asked & rising',
    tone: 'success',
    help: 'Asked in approved interview records, and the latest research shows demand rising.',
  },
  rising_in_market: {
    label: 'Rising in market',
    tone: 'brand',
    help: 'Research shows rising or emerging demand; no approved interview evidence yet.',
  },
  asked: { label: 'Asked in interviews', tone: 'neutral', help: 'Approved interview evidence; no rising market signal.' },
  declining: { label: 'Declining', tone: 'warning', help: 'The latest research finding shows declining demand.' },
  no_evidence: { label: 'No evidence yet', tone: 'neutral', help: 'No approved interview records or research findings.' },
}

const LEVEL_ICONS = {
  info: <Info className="mt-0.5 size-3.5 shrink-0 text-slate-400" aria-label="Info" />,
  warning: <TriangleAlert className="mt-0.5 size-3.5 shrink-0 text-amber-500" aria-label="Warning" />,
  error: <CircleAlert className="mt-0.5 size-3.5 shrink-0 text-rose-500" aria-label="Error" />,
}

const timeOnly = new Intl.DateTimeFormat(undefined, { hour: 'numeric', minute: '2-digit', second: '2-digit' })

function payloadSummary(kind: JobKind, payload: Record<string, unknown>): string | null {
  if (kind === 'exploration') {
    return [
      payload.fetch_first ? 'Fetched new records first' : null,
      `up to ${payload.max_records} records`,
      `spending limit ${formatUsd(String(payload.max_cost_usd))}`,
    ]
      .filter(Boolean)
      .join(' · ')
  }
  if (kind === 'market_research') {
    const roles = (payload.roles as string[] | undefined)?.join(', ')
    return [roles, payload.region, `last ${payload.months} months`, `limit ${formatUsd(String(payload.max_cost_usd))}`]
      .filter(Boolean)
      .join(' · ')
  }
  if (kind === 'content_generation') {
    return [
      (payload.components as string[] | undefined)?.join(', '),
      payload.use_intelligence ? 'used approved intelligence' : 'no intelligence',
      `limit ${formatUsd(String(payload.max_cost_usd))}`,
    ]
      .filter(Boolean)
      .join(' · ')
  }
  if (kind === 'content_narration') return `Voice ${String(payload.voice).split(':')[0]}`
  return null
}

/** Any run's details: counts, cost, settings and its log, with Stop and Retry.
 * `scope="content"` reads through the content studio's endpoints (for content staff). */
export function AgentRunDialog({ jobId, onClose, scope = 'agents' }: { jobId: string; onClose: () => void; scope?: 'agents' | 'content' }) {
  const agentJob = useAgentJob(jobId, scope === 'agents')
  const contentJob = useContentJob(jobId, scope === 'content')
  const job = scope === 'agents' ? agentJob : contentJob
  const stopAgent = useStopAgentJob()
  const stopContent = useStopContentJob()
  const stop = scope === 'agents' ? stopAgent : stopContent
  const retry = useRetryAgentJob()
  const toast = useToast()
  const canRunAgents = useCan('agents.run')
  const canManageSources = useCan('sources.manage')
  const canGenerate = useCan('content.generate')
  const data = job.data
  const isContent = !!data && CONTENT_KINDS.includes(data.kind)
  const contentTopic = data && 'topic' in data ? (data as ContentJobDetail).topic : null
  const canControl =
    data && (isContent ? canGenerate : data.kind === 'exploration' || data.kind === 'market_research' ? canRunAgents : canManageSources)
  const settings = data ? payloadSummary(data.kind, data.payload) : null

  return (
    <Dialog
      open
      onClose={onClose}
      size="lg"
      title={data ? `${KIND_LABELS[data.kind]}${data.source_name ? ` · ${data.source_name}` : ''}` : 'Run'}
      description={
        data
          ? `Started ${formatDateTime(data.started_at ?? data.created_at)}${data.triggered_by ? ` by ${data.triggered_by}` : ''}${duration(data) ? ` · took ${duration(data)}` : ''}`
          : undefined
      }
      footer={
        <>
          {data && canControl && isActive(data) && !data.cancel_requested && (
            <Button
              variant="secondary"
              icon={<Square className="size-3.5" />}
              loading={stop.isPending}
              onClick={() => stop.mutate(data.id, { onError: (e) => toast.error(errorMessage(e)) })}
            >
              Stop
            </Button>
          )}
          {data && canControl && !isActive(data) && data.kind !== 'source_import' && !isContent && (
            <Button
              variant="secondary"
              icon={<RotateCcw className="size-3.5" />}
              loading={retry.isPending}
              onClick={() =>
                retry.mutate(data.id, {
                  onSuccess: () => {
                    toast.success('Started again with the same settings')
                    onClose()
                  },
                  onError: (e) => toast.error(errorMessage(e)),
                })
              }
            >
              Run again
            </Button>
          )}
          <Button onClick={onClose}>Close</Button>
        </>
      }
    >
      {job.isPending ? (
        <div className="space-y-3">
          <Skeleton className="h-16" />
          <Skeleton className="h-40" />
        </div>
      ) : job.isError ? (
        <Alert>{errorMessage(job.error)}</Alert>
      ) : (
        <div className="space-y-5">
          <div className="flex flex-wrap items-center gap-2">
            <JobStatusBadge status={job.data.status} />
            <Badge>
              Cost {formatUsd(job.data.cost_usd)}
            </Badge>
            {job.data.report_id && (
              <Link
                to={`/admin/agents/research/${job.data.report_id}`}
                className="inline-flex items-center gap-1 text-sm font-semibold text-brand-700 hover:underline"
              >
                Open the report <ArrowUpRight className="size-3.5" aria-hidden />
              </Link>
            )}
            {contentTopic && (
              <Link
                to={`/admin/content/${contentTopic.id}`}
                className="inline-flex items-center gap-1 text-sm font-semibold text-brand-700 hover:underline"
              >
                Open {contentTopic.name} <ArrowUpRight className="size-3.5" aria-hidden />
              </Link>
            )}
            {job.data.kind === 'exploration' && Number(job.data.result.questions ?? 0) > 0 && (
              <Link
                to="/admin/intelligence"
                className="inline-flex items-center gap-1 text-sm font-semibold text-brand-700 hover:underline"
              >
                Review the questions <ArrowUpRight className="size-3.5" aria-hidden />
              </Link>
            )}
          </div>
          {settings && <p className="text-xs text-slate-500">{settings}</p>}
          {job.data.error && <Alert>{job.data.error}</Alert>}
          <dl className="grid grid-cols-2 gap-2 sm:grid-cols-3">
            {resultCounts(job.data).map(({ label, value }) => (
              <div key={label} className="rounded-xl bg-slate-50 px-3 py-2.5 ring-1 ring-slate-200/70">
                <dt className="text-xs text-slate-500">{label}</dt>
                <dd className="font-display text-xl font-semibold text-slate-900 tabular-nums">{value}</dd>
              </div>
            ))}
          </dl>
          <section>
            <h3 className="mb-2 text-sm font-semibold text-slate-900">Log</h3>
            <ol className="max-h-80 space-y-1.5 overflow-y-auto rounded-xl bg-slate-950 p-3 font-mono text-xs text-slate-200">
              {job.data.events.map((event, index) => (
                <li key={index} className="flex gap-2">
                  {LEVEL_ICONS[event.level]}
                  <span className="shrink-0 text-slate-500 tabular-nums">{timeOnly.format(new Date(event.created_at))}</span>
                  <span className="min-w-0 break-words">{event.message}</span>
                </li>
              ))}
            </ol>
          </section>
        </div>
      )}
    </Dialog>
  )
}
