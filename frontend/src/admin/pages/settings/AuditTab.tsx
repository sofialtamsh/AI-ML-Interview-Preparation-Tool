import { ScrollText } from 'lucide-react'
import { useState } from 'react'

import { Pagination } from '../../../components/Pagination'
import { Alert, Card, EmptyState, Skeleton } from '../../../components/ui/Feedback'
import { SelectField } from '../../../components/ui/Field'
import { errorMessage } from '../../../lib/api'
import { cn } from '../../../lib/cn'
import { formatDateTime } from '../../../lib/format'
import { useAuditLogs } from '../../api'

const ACTION_LABELS: Record<string, string> = {
  'student.updated': 'Updated a student',
  'cohort.created': 'Created a cohort',
  'admin_user.created': 'Added an admin',
  'admin_user.updated': 'Updated an admin',
  'role.created': 'Created a role',
  'role.updated': 'Updated a role',
  'role.deleted': 'Deleted a role',
  'source.created': 'Added an interview source',
  'source.updated': 'Edited an interview source',
  'source.removed': 'Removed an interview source',
  'source.credentials_set': 'Set source credentials',
  'source.credentials_cleared': 'Deleted source credentials',
  'source.connection_tested': 'Tested a source connection',
  'source.fetch_started': 'Started a source fetch',
  'source.fetch_stopped': 'Stopped a source fetch',
  'source.file_imported': 'Imported a file into a source',
  'agent.exploration_started': 'Started the Exploration agent',
  'agent.research_started': 'Started market research',
  'agent.run_stopped': 'Stopped an agent run',
  'agent.run_retried': 'Re-ran an agent run',
  'intelligence.question_reviewed': 'Reviewed an interview question',
  'intelligence.questions_reviewed': 'Reviewed interview questions',
  'intelligence.interview_corrected': 'Corrected interview details',
  'research.recommendation_decided': 'Decided on a curriculum recommendation',
  'research.question_reviewed': 'Reviewed a research-derived question',
  'content.edited': 'Edited content (new version)',
  'content.submit': 'Sent content for review',
  'content.send_back': 'Sent content back to draft',
  'content.reject': 'Rejected content',
  'content.approve': 'Approved content',
  'content.publish': 'Published content',
  'content.unpublish': 'Unpublished content',
  'content.archive': 'Archived content',
  'content.bulk_submit': 'Sent a topic for review',
  'content.bulk_approve': 'Approved a topic',
  'content.bulk_publish': 'Published a topic',
  'content.restored': 'Restored an older content version',
  'content.code_checked': 'Ran a Python lab check',
  'content.generation_started': 'Started content generation',
  'content.narration_started': 'Started narration',
  'content.run_stopped': 'Stopped a content run',
  'content.expansion_decided': 'Decided on content expansion',
  'taxonomy.domain_created': 'Added a domain',
  'taxonomy.domain_updated': 'Edited a domain',
  'taxonomy.topic_created': 'Added a topic',
  'taxonomy.topic_updated': 'Edited a topic',
}

const FILTERS = [
  { value: '', label: 'All activity' },
  { value: 'student.', label: 'Students' },
  { value: 'cohort.', label: 'Cohorts' },
  { value: 'admin_user.', label: 'Admins' },
  { value: 'role.', label: 'Roles' },
  { value: 'source.', label: 'Interview sources' },
  { value: 'agent.', label: 'Agent runs' },
  { value: 'intelligence.', label: 'Intelligence review' },
  { value: 'research.', label: 'Research decisions' },
  { value: 'content.', label: 'Content' },
  { value: 'taxonomy.', label: 'Domains & topics' },
]

function show(value: unknown): string {
  if (value === null || value === undefined || value === '') return '—'
  if (Array.isArray(value)) return value.length ? value.join(', ') : '—'
  return String(value)
}

/** Turns {"status": {"from": "active", "to": "suspended"}} into readable lines. */
export function describeDetails(details: Record<string, unknown>): string[] {
  return Object.entries(details).map(([key, value]) => {
    const label = key.replace(/_/g, ' ')
    if (value && typeof value === 'object' && !Array.isArray(value) && 'to' in value) {
      const change = value as { from?: unknown; to?: unknown }
      return `${label}: ${show(change.from)} → ${show(change.to)}`
    }
    return `${label}: ${show(value)}`
  })
}

const PAGE_SIZE = 25

export default function AuditTab() {
  const [page, setPage] = useState(1)
  const [action, setAction] = useState('')
  const logs = useAuditLogs(page, action)

  return (
    <Card className="overflow-hidden">
      <div className="flex flex-wrap items-center justify-between gap-3 border-b border-slate-100 px-5 py-4">
        <div>
          <h2 className="font-display text-base font-semibold text-slate-900">Audit log</h2>
          <p className="text-sm text-slate-500">Every privileged admin action, newest first.</p>
        </div>
        <div className="w-52">
          <SelectField
            label="Filter activity"
            hideLabel
            value={action}
            onChange={(e) => {
              setAction(e.target.value)
              setPage(1)
            }}
          >
            {FILTERS.map((f) => (
              <option key={f.value} value={f.value}>
                {f.label}
              </option>
            ))}
          </SelectField>
        </div>
      </div>
      {logs.isPending ? (
        <div className="space-y-3 p-5">
          {[0, 1, 2].map((i) => (
            <Skeleton key={i} className="h-12" />
          ))}
        </div>
      ) : logs.isError ? (
        <div className="p-5">
          <Alert>{errorMessage(logs.error)}</Alert>
        </div>
      ) : logs.data.total === 0 ? (
        <EmptyState icon={<ScrollText className="size-6" />} title="Nothing recorded yet">
          Admin actions such as suspending a student or changing a role will appear here.
        </EmptyState>
      ) : (
        <>
          <ul className={cn('divide-y divide-slate-100 transition-opacity', logs.isPlaceholderData && 'opacity-60')}>
            {logs.data.items.map((entry) => (
              <li key={entry.id} className="grid gap-1 px-5 py-3.5 sm:grid-cols-[180px_minmax(0,1fr)] sm:gap-4">
                <time className="text-xs text-slate-500 sm:pt-0.5" dateTime={entry.created_at}>
                  {formatDateTime(entry.created_at)}
                </time>
                <div className="min-w-0">
                  <p className="text-sm text-slate-900">
                    <span className="font-semibold">{entry.actor_name ?? 'Deleted admin'}</span>{' '}
                    {(ACTION_LABELS[entry.action] ?? entry.action).toLowerCase()}
                    {entry.entity_id && (
                      <span className="ml-1.5 font-mono text-xs text-slate-400">
                        {entry.entity_type}:{entry.entity_id.slice(0, 8)}
                      </span>
                    )}
                  </p>
                  <ul className="mt-0.5 text-xs text-slate-600">
                    {describeDetails(entry.details).map((line) => (
                      <li key={line} className="truncate">
                        {line}
                      </li>
                    ))}
                  </ul>
                </div>
              </li>
            ))}
          </ul>
          <Pagination page={logs.data.page} pageSize={PAGE_SIZE} total={logs.data.total} onPage={setPage} />
        </>
      )}
    </Card>
  )
}
