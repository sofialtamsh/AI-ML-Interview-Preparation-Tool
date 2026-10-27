import { Braces, FileUp, Globe, Rss, type LucideIcon } from 'lucide-react'

import { Badge, Spinner } from '../../../components/ui/Feedback'
import { cn } from '../../../lib/cn'
import type { ConnectionStatus, ConnectorType, JobStatus, JobSummary, RunCounts } from '../../../lib/types'

export const CONNECTOR_ICONS: Record<ConnectorType, LucideIcon> = {
  web_pages: Globe,
  json_api: Braces,
  rss_feed: Rss,
  file_upload: FileUp,
}

export function TypeTile({ type, className }: { type: ConnectorType; className?: string }) {
  const Icon = CONNECTOR_ICONS[type]
  return (
    <span
      className={cn(
        'grid shrink-0 place-items-center rounded-xl bg-gradient-to-br from-brand-50 to-fuchsia-50 text-brand-600 ring-1 ring-brand-100',
        className ?? 'size-10',
      )}
    >
      <Icon className="size-5" aria-hidden />
    </span>
  )
}

const CONNECTION = {
  untested: { tone: 'neutral', label: 'Not tested' },
  ok: { tone: 'success', label: 'Connected' },
  failed: { tone: 'danger', label: 'Connection failed' },
  manual_import_required: { tone: 'warning', label: 'Manual import' },
} as const

export function ConnectionBadge({ status }: { status: ConnectionStatus }) {
  const { tone, label } = CONNECTION[status]
  return (
    <Badge tone={tone}>
      <span className="size-1.5 rounded-full bg-current" aria-hidden />
      {label}
    </Badge>
  )
}

const JOB = {
  queued: { tone: 'neutral', label: 'Queued' },
  running: { tone: 'brand', label: 'Running' },
  succeeded: { tone: 'success', label: 'Succeeded' },
  completed_with_errors: { tone: 'warning', label: 'Finished with issues' },
  failed: { tone: 'danger', label: 'Failed' },
  cancelled: { tone: 'neutral', label: 'Stopped' },
} as const

export function JobStatusBadge({ status }: { status: JobStatus }) {
  const { tone, label } = JOB[status]
  return (
    <Badge tone={tone}>
      {status === 'running' || status === 'queued' ? (
        <Spinner className="size-3" />
      ) : (
        <span className="size-1.5 rounded-full bg-current" aria-hidden />
      )}
      {label}
    </Badge>
  )
}

export const isActive = (job: Pick<JobSummary, 'status'>) =>
  job.status === 'queued' || job.status === 'running'

export function jobTitle(job: JobSummary): string {
  return job.kind === 'source_import' ? `Import · ${job.file_name ?? 'file'}` : 'Fetch'
}

/** "3 new · 1 updated · 12 unchanged" (only the parts that happened). */
export function runSummary(counts: RunCounts): string {
  const parts = [
    counts.new ? `${counts.new} new` : null,
    counts.updated ? `${counts.updated} updated` : null,
    counts.unchanged ? `${counts.unchanged} unchanged` : null,
    counts.skipped_known ? `${counts.skipped_known} already fetched` : null,
  ].filter(Boolean)
  return parts.length ? parts.join(' · ') : 'No records'
}

export function duration(job: JobSummary): string | null {
  if (!job.started_at || !job.finished_at) return null
  const seconds = Math.max(0, Math.round((Date.parse(job.finished_at) - Date.parse(job.started_at)) / 1000))
  if (seconds < 60) return `${seconds}s`
  const minutes = Math.floor(seconds / 60)
  return `${minutes}m ${seconds % 60}s`
}

export function hostOf(url: string | null): string | null {
  if (!url) return null
  try {
    return new URL(url).host
  } catch {
    return url
  }
}
