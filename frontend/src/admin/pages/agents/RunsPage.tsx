import { Activity } from 'lucide-react'
import { useState } from 'react'

import { Pagination } from '../../../components/Pagination'
import { Alert, Card, EmptyState, PageHeader, Skeleton } from '../../../components/ui/Feedback'
import { SelectField } from '../../../components/ui/Field'
import { errorMessage } from '../../../lib/api'
import { formatDateTime, formatUsd, timeAgo } from '../../../lib/format'
import type { JobKind, JobStatus } from '../../../lib/types'
import { useAgentJobs } from '../../intelApi'
import { duration, JobStatusBadge } from '../sources/shared'
import { AgentRunDialog, KIND_LABELS, runHeadline } from './shared'

const STATUSES: [JobStatus, string][] = [
  ['running', 'Running'],
  ['queued', 'Queued'],
  ['succeeded', 'Succeeded'],
  ['completed_with_errors', 'Finished with issues'],
  ['failed', 'Failed'],
  ['cancelled', 'Stopped'],
]

export default function RunsPage() {
  const [kind, setKind] = useState<JobKind | ''>('')
  const [status, setStatus] = useState<JobStatus | ''>('')
  const [page, setPage] = useState(1)
  const [open, setOpen] = useState<string | null>(null)
  const runs = useAgentJobs({ kind, status, page, pageSize: 20 })

  return (
    <div>
      <PageHeader
        title="Agent runs"
        description="Every fetch, import and agent run, with its log and AI cost. Kept permanently."
      />
      <Card className="overflow-hidden">
        <div className="flex flex-wrap gap-3 border-b border-slate-100 px-5 py-4">
          <div className="w-full sm:w-52">
            <SelectField
              label="Kind"
              hideLabel
              value={kind}
              onChange={(e) => {
                setKind(e.target.value as JobKind | '')
                setPage(1)
              }}
            >
              <option value="">All kinds</option>
              {Object.entries(KIND_LABELS).map(([key, label]) => (
                <option key={key} value={key}>
                  {label}
                </option>
              ))}
            </SelectField>
          </div>
          <div className="w-full sm:w-52">
            <SelectField
              label="Status"
              hideLabel
              value={status}
              onChange={(e) => {
                setStatus(e.target.value as JobStatus | '')
                setPage(1)
              }}
            >
              <option value="">Any status</option>
              {STATUSES.map(([key, label]) => (
                <option key={key} value={key}>
                  {label}
                </option>
              ))}
            </SelectField>
          </div>
        </div>
        {runs.isPending ? (
          <div className="space-y-2 p-5">
            <Skeleton className="h-12" />
            <Skeleton className="h-12" />
          </div>
        ) : runs.isError ? (
          <div className="p-5">
            <Alert>{errorMessage(runs.error)}</Alert>
          </div>
        ) : runs.data.items.length === 0 ? (
          <EmptyState icon={<Activity className="size-6" />} title={kind || status ? 'No matching runs' : 'No runs yet'}>
            Runs appear here when someone fetches a source, imports a file or starts an agent.
          </EmptyState>
        ) : (
          <>
            <div className="overflow-x-auto">
              <table className="w-full min-w-[760px] text-left text-sm">
                <thead className="border-b border-slate-100 bg-slate-50/80 text-xs text-slate-500">
                  <tr>
                    <th className="px-5 py-3 font-medium">Run</th>
                    <th className="px-3 py-3 font-medium">Status</th>
                    <th className="px-3 py-3 font-medium">Outcome</th>
                    <th className="px-3 py-3 text-right font-medium">AI cost</th>
                    <th className="px-5 py-3 font-medium">Started</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100">
                  {runs.data.items.map((job) => (
                    <tr key={job.id} className="cursor-pointer transition hover:bg-slate-50" onClick={() => setOpen(job.id)}>
                      <td className="px-5 py-3">
                        <button type="button" className="text-left font-medium text-slate-900 hover:text-brand-700" onClick={() => setOpen(job.id)}>
                          {KIND_LABELS[job.kind]}
                        </button>
                        <p className="text-xs text-slate-500">{job.source_name ?? job.file_name ?? (job.kind === 'market_research' ? 'Web research' : '')}</p>
                      </td>
                      <td className="px-3 py-3">
                        <JobStatusBadge status={job.status} />
                      </td>
                      <td className="max-w-xs truncate px-3 py-3 text-slate-600" title={runHeadline(job)}>
                        {runHeadline(job)}
                      </td>
                      <td className="px-3 py-3 text-right text-slate-700 tabular-nums">{formatUsd(job.cost_usd)}</td>
                      <td className="px-5 py-3 text-slate-600">
                        <span title={formatDateTime(job.created_at)}>{timeAgo(job.created_at)}</span>
                        <span className="block text-xs text-slate-500">
                          {[job.triggered_by, duration(job)].filter(Boolean).join(' · ')}
                        </span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            {runs.data.total > 20 && <Pagination page={page} pageSize={20} total={runs.data.total} onPage={setPage} />}
          </>
        )}
      </Card>
      {open && <AgentRunDialog jobId={open} onClose={() => setOpen(null)} />}
    </div>
  )
}
