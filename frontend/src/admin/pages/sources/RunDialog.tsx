import { CircleAlert, Info, TriangleAlert } from 'lucide-react'

import { Button } from '../../../components/ui/Button'
import { Dialog } from '../../../components/ui/Dialog'
import { Alert, Skeleton } from '../../../components/ui/Feedback'
import { errorMessage } from '../../../lib/api'
import { formatDateTime } from '../../../lib/format'
import type { JobDetail } from '../../../lib/types'
import { useSourceJob } from '../../api'
import { duration, isActive, jobTitle, JobStatusBadge } from './shared'

const LEVEL_ICONS = {
  info: <Info className="mt-0.5 size-3.5 shrink-0 text-slate-400" aria-label="Info" />,
  warning: <TriangleAlert className="mt-0.5 size-3.5 shrink-0 text-amber-600" aria-label="Warning" />,
  error: <CircleAlert className="mt-0.5 size-3.5 shrink-0 text-rose-600" aria-label="Error" />,
}

const COUNTS: { key: keyof JobDetail['result']; label: string }[] = [
  { key: 'new', label: 'New' },
  { key: 'updated', label: 'Updated' },
  { key: 'unchanged', label: 'Unchanged' },
  { key: 'skipped_known', label: 'Already fetched' },
]

const timeOnly = new Intl.DateTimeFormat(undefined, { hour: 'numeric', minute: '2-digit', second: '2-digit' })

export function RunDialog({
  sourceId,
  jobId,
  onClose,
  onShowRecords,
}: {
  sourceId: string
  jobId: string
  onClose: () => void
  onShowRecords?: () => void
}) {
  const job = useSourceJob(sourceId, jobId)
  const data = job.data

  return (
    <Dialog
      open
      onClose={onClose}
      size="lg"
      title={data ? jobTitle(data) : 'Run'}
      description={
        data
          ? `Started ${formatDateTime(data.started_at ?? data.created_at)}${data.triggered_by ? ` by ${data.triggered_by}` : ''}${duration(data) ? ` · took ${duration(data)}` : ''}`
          : undefined
      }
      footer={
        <>
          {onShowRecords && data && ((data.result.new ?? 0) > 0 || (data.result.updated ?? 0) > 0) && (
            <Button variant="secondary" onClick={onShowRecords}>
              View records from this run
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
            {isActive(job.data) && (
              <span className="text-xs text-slate-500">Updates live · {job.data.progress_done} saved so far</span>
            )}
          </div>
          {job.data.error && <Alert>{job.data.error}</Alert>}
          <dl className="grid grid-cols-2 gap-2 sm:grid-cols-4">
            {COUNTS.map(({ key, label }) => (
              <div key={key} className="rounded-xl bg-slate-50 px-3 py-2.5 ring-1 ring-slate-200/70">
                <dt className="text-xs text-slate-500">{label}</dt>
                <dd className="font-display text-xl font-semibold text-slate-900 tabular-nums">
                  {job.data.result[key] ?? 0}
                </dd>
              </div>
            ))}
          </dl>
          <section>
            <h3 className="mb-2 text-sm font-semibold text-slate-900">Log</h3>
            <ol className="max-h-80 space-y-1.5 overflow-y-auto rounded-xl bg-slate-950 p-3 font-mono text-xs text-slate-200">
              {job.data.events.map((event, index) => (
                <li key={index} className="flex gap-2">
                  {LEVEL_ICONS[event.level]}
                  <span className="shrink-0 text-slate-500 tabular-nums">
                    {timeOnly.format(new Date(event.created_at))}
                  </span>
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
