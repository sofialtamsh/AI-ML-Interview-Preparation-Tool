import { Activity } from 'lucide-react'
import { useState } from 'react'

import { Alert, Badge, EmptyState, Skeleton } from '../../../components/ui/Feedback'
import { SECTIONS } from '../../../learn/sections'
import { errorMessage } from '../../../lib/api'
import { formatUsd, timeAgo } from '../../../lib/format'
import type { ContentComponent, InterviewEntry, NarrationClip, VersionOrigin, VersionStatus } from '../../../lib/types'
import { useContentJobs } from '../../contentApi'
import { AgentRunDialog, KIND_LABELS, runHeadline } from '../agents/shared'
import { JobStatusBadge } from '../sources/shared'

type Tone = 'neutral' | 'brand' | 'success' | 'warning' | 'danger'

export const VERSION_STATUS: Record<VersionStatus, { label: string; tone: Tone; dot: string }> = {
  draft: { label: 'Draft', tone: 'neutral', dot: 'bg-slate-400' },
  under_review: { label: 'In review', tone: 'warning', dot: 'bg-amber-500' },
  approved: { label: 'Approved', tone: 'brand', dot: 'bg-brand-500' },
  published: { label: 'Published', tone: 'success', dot: 'bg-emerald-500' },
  rejected: { label: 'Rejected', tone: 'danger', dot: 'bg-rose-500' },
  archived: { label: 'Archived', tone: 'neutral', dot: 'bg-slate-300' },
}

export const ORIGIN_LABELS: Record<VersionOrigin, string> = {
  starter: 'Starter draft',
  ai_generated: 'AI generated',
  edited: 'Edited',
}

export function VersionStatusBadge({ status }: { status: VersionStatus }) {
  const { label, tone, dot } = VERSION_STATUS[status]
  return (
    <Badge tone={tone}>
      <span className={`size-1.5 rounded-full ${dot}`} aria-hidden />
      {label}
    </Badge>
  )
}

export const componentLabel = (component: ContentComponent) => SECTIONS[component].admin

const STUDENT_LABELS: Record<string, InterviewEntry['label']> = {
  ai_generated: 'Practice question',
  admin_created: 'Practice question',
  actual_interview: 'Asked in real interviews',
  research_derived: 'In demand right now',
}

/** The body as a student would receive it (mirrors app/schemas/learn.py), for previews. */
export function studentView(component: ContentComponent, body: Record<string, unknown>, narration: NarrationClip[]): unknown {
  if (component === 'interview') {
    const questions = (body.questions as Record<string, unknown>[]).map((q) => ({
      ...q,
      label: STUDENT_LABELS[String(q.origin)] ?? 'Practice question',
      asked_for_role: q.origin === 'actual_interview' ? (q.asked_for_role ?? null) : null,
    }))
    return { ...body, questions }
  }
  if (component === 'video') {
    const audio = new Map(narration.map((clip) => [clip.position, clip.id]))
    const scenes = (body.scenes as Record<string, unknown>[]).map((scene, i) => ({ ...scene, audio_id: audio.get(i) ?? null }))
    return { ...body, scenes }
  }
  return body
}

/** Recent generation and narration runs, optionally for one topic, each opening its log. */
export function ContentRuns({ topicId, pageSize = 6 }: { topicId?: string; pageSize?: number }) {
  const runs = useContentJobs(topicId, pageSize)
  const [open, setOpen] = useState<string | null>(null)

  if (runs.isPending) return <Skeleton className="m-5 h-24" />
  if (runs.isError) return <Alert className="m-5">{errorMessage(runs.error)}</Alert>
  if (runs.data.items.length === 0) {
    return (
      <EmptyState icon={<Activity className="size-6" />} title="No runs yet" className="py-8">
        Generation and narration runs appear here with their log and cost.
      </EmptyState>
    )
  }
  return (
    <>
      <ul className="divide-y divide-slate-100">
        {runs.data.items.map((job) => (
          <li key={job.id}>
            <button type="button" onClick={() => setOpen(job.id)} className="flex w-full flex-wrap items-center gap-x-3 gap-y-1 px-5 py-3 text-left transition hover:bg-slate-50">
              <JobStatusBadge status={job.status} />
              <span className="min-w-0 flex-1">
                <span className="block text-sm font-medium text-slate-900">
                  {KIND_LABELS[job.kind]}
                  {job.topic && !topicId ? ` · ${job.topic.name}` : ''}
                </span>
                <span className="block truncate text-xs text-slate-500">{runHeadline(job)}</span>
              </span>
              <span className="text-xs text-slate-500">
                {formatUsd(job.cost_usd)} · {timeAgo(job.created_at)}
              </span>
            </button>
          </li>
        ))}
      </ul>
      {open && <AgentRunDialog jobId={open} scope="content" onClose={() => setOpen(null)} />}
    </>
  )
}
