import { useQueryClient } from '@tanstack/react-query'
import {
  Activity,
  Archive,
  ArrowLeft,
  ExternalLink,
  FileUp,
  KeyRound,
  Pencil,
  Play,
  PlugZap,
  Square,
} from 'lucide-react'
import { useEffect, useRef, useState, type ReactNode } from 'react'
import { Link, useNavigate, useParams } from 'react-router'

import { Pagination } from '../../../components/Pagination'
import { Button } from '../../../components/ui/Button'
import { Dialog } from '../../../components/ui/Dialog'
import { Alert, Badge, Card, CardHeader, EmptyState, Skeleton } from '../../../components/ui/Feedback'
import { useToast } from '../../../components/ui/Toast'
import { api, errorMessage } from '../../../lib/api'
import { formatDateTime, timeAgo } from '../../../lib/format'
import { adminKeys } from '../../../lib/queryClient'
import type { FieldSpec, JobDetail, JobSummary, SourceCatalog, SourceDetail } from '../../../lib/types'
import {
  useCan,
  useFetchSource,
  useRemoveSource,
  useSource,
  useSourceCatalog,
  useSourceJobs,
  useStopJob,
  useTestSource,
} from '../../api'
import { CredentialsDialog } from './CredentialsDialog'
import { RecordsCard } from './RecordsCard'
import { RunDialog } from './RunDialog'
import {
  ConnectionBadge,
  duration,
  hostOf,
  isActive,
  jobTitle,
  JobStatusBadge,
  runSummary,
  TypeTile,
} from './shared'
import { isVisible } from './settingsForm'
import { SourceDialog } from './SourceDialog'
import { UploadDialog } from './UploadDialog'

type Panel = 'edit' | 'credentials' | 'upload' | 'remove' | null

function fetchBlocker(source: SourceDetail): string | null {
  if (source.removed_at) return 'This source was removed.'
  if (!source.enabled) return 'Turn the source on to fetch it.'
  if (source.connector_type === 'file_upload') return null
  if (!source.credentials.complete) return 'Add credentials first.'
  return null
}

function Row({ label, children }: { label: string; children: ReactNode }) {
  return (
    <div className="flex justify-between gap-4 py-2 text-sm">
      <dt className="shrink-0 text-slate-500">{label}</dt>
      <dd className="min-w-0 text-right text-slate-900">{children}</dd>
    </div>
  )
}

function show(field: FieldSpec, value: unknown): string | null {
  if (value === null || value === undefined || value === '') return null
  if (Array.isArray(value)) return value.length ? value.join(', ') : null
  if (typeof value === 'boolean') return value ? 'Yes' : 'No'
  if (field.kind === 'select') return field.options?.find((o) => o.value === value)?.label ?? String(value)
  return String(value)
}

function SettingsSummary({ catalog, source }: { catalog: SourceCatalog; source: SourceDetail }) {
  const connector = catalog.connectors.find((c) => c.key === source.connector_type)
  const auth = catalog.auth_methods.find((m) => m.key === source.auth_method)
  // Only settings that apply (e.g. no cursor parameter when pagination is by page number).
  const applicable = (fields: FieldSpec[], values: Record<string, unknown>) =>
    fields.filter((f) => isVisible(f, values)).map((f) => [f, values[f.key]] as const)
  const rows = [
    ...applicable(auth?.settings_fields ?? [], source.auth_config),
    ...applicable(connector?.settings_fields ?? [], source.config),
  ]
    .map(([field, value]) => [field.label, show(field, value)] as const)
    .filter((row): row is readonly [string, string] => row[1] !== null)
  if (!rows.length) return <p className="px-5 py-4 text-sm text-slate-500">No extra settings.</p>
  return (
    <dl className="divide-y divide-slate-100 px-5 py-1">
      {rows.map(([label, value]) => (
        <Row key={label} label={label}>
          <span className="break-words">{value}</span>
        </Row>
      ))}
    </dl>
  )
}

function RunHistory({
  source,
  onOpen,
}: {
  source: SourceDetail
  onOpen: (job: JobSummary) => void
}) {
  const [page, setPage] = useState(1)
  const jobs = useSourceJobs(source.id, page, !!source.active_job)
  return (
    <Card className="overflow-hidden">
      <CardHeader title="Run history" description="Every fetch and import, kept permanently." />
      {jobs.isPending ? (
        <div className="space-y-2 p-5">
          <Skeleton className="h-12" />
          <Skeleton className="h-12" />
        </div>
      ) : jobs.isError ? (
        <div className="p-5">
          <Alert>{errorMessage(jobs.error)}</Alert>
        </div>
      ) : jobs.data.items.length === 0 ? (
        <EmptyState icon={<Activity className="size-6" />} title="No runs yet">
          {source.connector_type === 'file_upload'
            ? 'Import files to add records.'
            : 'Test the connection, then fetch. Each run is listed here with its log.'}
        </EmptyState>
      ) : (
        <>
          <ul className="divide-y divide-slate-100">
            {jobs.data.items.map((job) => (
              <li key={job.id}>
                <button
                  type="button"
                  onClick={() => onOpen(job)}
                  className="flex w-full flex-wrap items-center gap-x-3 gap-y-1 px-5 py-3 text-left transition hover:bg-slate-50"
                >
                  <JobStatusBadge status={job.status} />
                  <span className="min-w-0 flex-1">
                    <span className="block truncate text-sm font-medium text-slate-900">{jobTitle(job)}</span>
                    <span className="block truncate text-xs text-slate-500">
                      {job.error ?? (isActive(job) ? `${job.progress_done} saved so far` : runSummary(job.result))}
                    </span>
                  </span>
                  <span className="text-right text-xs text-slate-500">
                    {timeAgo(job.created_at)}
                    {duration(job) && <span className="block">{duration(job)}</span>}
                  </span>
                </button>
              </li>
            ))}
          </ul>
          {jobs.data.total > 8 && (
            <Pagination page={page} pageSize={8} total={jobs.data.total} onPage={setPage} />
          )}
        </>
      )}
    </Card>
  )
}

/** Refreshes history and records when a running fetch ends, and says how it went. */
function useFetchFinished(source: SourceDetail | undefined) {
  const queryClient = useQueryClient()
  const toast = useToast()
  const activeId = source?.active_job?.id ?? null
  const previous = useRef<string | null>(activeId)
  useEffect(() => {
    const finished = previous.current
    previous.current = activeId
    if (!source || !finished || activeId === finished) return
    queryClient.invalidateQueries({ queryKey: adminKeys.sourceJobs(source.id) })
    queryClient.invalidateQueries({ queryKey: adminKeys.sourceRecords(source.id) })
    queryClient.invalidateQueries({ queryKey: adminKeys.sources })
    api<JobDetail>(`/admin/sources/${source.id}/jobs/${finished}`)
      .then((job) => {
        if (job.status === 'succeeded') toast.success(`Fetch finished: ${runSummary(job.result)}`)
        else if (job.status === 'completed_with_errors') toast.error('Fetch finished with some problems. See its log.')
        else if (job.status === 'failed') toast.error(job.error ?? 'The fetch failed.')
      })
      .catch(() => {})
  }, [activeId, source, queryClient, toast])
}

export default function SourceDetailPage() {
  const { id = '' } = useParams()
  const source = useSource(id)
  const catalog = useSourceCatalog()
  const canManage = useCan('sources.manage')
  const canSetCredentials = useCan('sources.credentials.manage')
  const canReadRecords = useCan('intelligence.view')
  const [panel, setPanel] = useState<Panel>(null)
  const [run, setRun] = useState<JobSummary | null>(null)
  const [jobFilter, setJobFilter] = useState<{ id: string; label: string } | null>(null)
  const test = useTestSource(id)
  const fetchNow = useFetchSource(id)
  const stop = useStopJob(id)
  const remove = useRemoveSource(id)
  const toast = useToast()
  const navigate = useNavigate()
  useFetchFinished(source.data)

  if (source.isPending || catalog.isPending) {
    return (
      <div className="space-y-4">
        <Skeleton className="h-24 rounded-2xl" />
        <Skeleton className="h-64 rounded-2xl" />
      </div>
    )
  }
  if (source.isError || catalog.isError) {
    return <Alert>{errorMessage(source.error ?? catalog.error)}</Alert>
  }

  const s = source.data
  const connector = catalog.data.connectors.find((c) => c.key === s.connector_type)
  const auth = catalog.data.auth_methods.find((m) => m.key === s.auth_method)
  const removed = !!s.removed_at
  const isUpload = s.connector_type === 'file_upload'
  const blocker = fetchBlocker(s)
  const active = s.active_job

  return (
    <div>
      <Link
        to="/admin/sources"
        className="mb-5 inline-flex items-center gap-1.5 text-sm font-medium text-slate-600 hover:text-slate-900"
      >
        <ArrowLeft className="size-4" aria-hidden /> All sources
      </Link>

      <div className="mb-5 flex flex-wrap items-start gap-4">
        <TypeTile type={s.connector_type} className="size-14" />
        <div className="min-w-0 flex-1">
          <div className="flex flex-wrap items-center gap-2">
            <h1 className="font-display text-2xl font-bold tracking-tight text-slate-900">{s.name}</h1>
            {removed ? <Badge>Removed</Badge> : !s.enabled ? <Badge>Off</Badge> : <ConnectionBadge status={s.connection_status} />}
          </div>
          <p className="mt-0.5 flex flex-wrap items-center gap-x-1.5 text-sm text-slate-500">
            {connector?.label}
            {s.base_url && (
              <>
                <span aria-hidden>·</span>
                <a
                  href={s.base_url}
                  target="_blank"
                  rel="noreferrer noopener"
                  className="inline-flex items-center gap-1 font-medium text-brand-700 hover:underline"
                >
                  {hostOf(s.base_url)} <ExternalLink className="size-3.5" aria-hidden />
                </a>
              </>
            )}
          </p>
          {s.description && <p className="mt-2 max-w-2xl text-sm text-slate-600">{s.description}</p>}
        </div>
      </div>

      {canManage && !removed && (
        <div className="mb-5 flex flex-wrap gap-2">
          {!isUpload && (
            <Button
              icon={<Play className="size-4" />}
              disabled={!!blocker || !!active}
              loading={fetchNow.isPending}
              title={blocker ?? undefined}
              onClick={() =>
                fetchNow.mutate(undefined, {
                  onSuccess: () => toast.success('Fetch started. It runs in the background.'),
                  onError: (error) => toast.error(errorMessage(error)),
                })
              }
            >
              Fetch now
            </Button>
          )}
          {!isUpload && (
            <Button
              variant="secondary"
              icon={<PlugZap className="size-4" />}
              loading={test.isPending}
              disabled={!s.credentials.complete}
              onClick={() =>
                test.mutate(undefined, {
                  onSuccess: (result) =>
                    result.connection_status === 'ok'
                      ? toast.success(result.connection_message ?? 'Connected')
                      : toast.error(result.connection_message ?? 'The connection test failed'),
                  onError: (error) => toast.error(errorMessage(error)),
                })
              }
            >
              Test connection
            </Button>
          )}
          <Button
            variant={isUpload ? 'primary' : 'secondary'}
            icon={<FileUp className="size-4" />}
            disabled={!s.enabled}
            title={!s.enabled ? 'Turn the source on to import files.' : undefined}
            onClick={() => setPanel('upload')}
          >
            Import files
          </Button>
          <Button variant="ghost" icon={<Pencil className="size-4" />} onClick={() => setPanel('edit')}>
            Edit
          </Button>
        </div>
      )}

      <div className="mb-5 space-y-3 empty:hidden">
        {active && (
          <Card className="flex flex-wrap items-center gap-3 p-4 ring-brand-200">
            <JobStatusBadge status={active.status} />
            <p className="flex-1 text-sm text-slate-700">
              {active.status === 'queued' ? 'Waiting to start…' : `Fetching… ${active.progress_done} records processed so far.`}
              {active.cancel_requested && ' Stopping after the current record.'}
            </p>
            <Button variant="ghost" size="sm" onClick={() => setRun(active)}>
              View log
            </Button>
            {canManage && !active.cancel_requested && (
              <Button
                variant="secondary"
                size="sm"
                icon={<Square className="size-3.5" />}
                loading={stop.isPending}
                onClick={() => stop.mutate(active.id, { onError: (error) => toast.error(errorMessage(error)) })}
              >
                Stop
              </Button>
            )}
          </Card>
        )}
        {!removed && !s.credentials.complete && (
          <Alert tone="info">
            This source signs in with {auth?.label.toLowerCase()}, so it needs credentials before it can be tested or
            fetched.{' '}
            {canSetCredentials ? (
              <button type="button" className="font-semibold underline" onClick={() => setPanel('credentials')}>
                Add credentials
              </button>
            ) : (
              'Ask an admin who can manage source credentials.'
            )}
          </Alert>
        )}
        {!removed && s.connection_status === 'manual_import_required' && !isUpload && (
          <Alert tone="info">
            This site doesn't allow automated access, and the platform never works around that. Export the pages
            yourself (as PDF, saved HTML or a spreadsheet) and use <strong>Import files</strong>.
          </Alert>
        )}
      </div>

      <div className="grid gap-5 lg:grid-cols-[minmax(0,1fr)_340px]">
        <div className="min-w-0 space-y-5">
          <RunHistory source={s} onOpen={setRun} />
          {canReadRecords && (
            <RecordsCard sourceId={s.id} jobFilter={jobFilter} onClearJobFilter={() => setJobFilter(null)} />
          )}
        </div>

        <div className="space-y-5">
          <Card>
            <CardHeader title="Status" />
            <dl className="divide-y divide-slate-100 px-5 py-1">
              <Row label="Connection">
                <ConnectionBadge status={s.connection_status} />
              </Row>
              {s.connection_message && (
                <p className="py-2 text-xs break-words text-slate-600">{s.connection_message}</p>
              )}
              {!isUpload && <Row label="Last tested">{timeAgo(s.last_tested_at)}</Row>}
              {!isUpload && (
                <Row label="Last successful fetch">
                  <span title={formatDateTime(s.last_successful_sync_at)}>{timeAgo(s.last_successful_sync_at)}</span>
                </Row>
              )}
              {!isUpload && (
                <Row label="Last attempt">
                  <span title={formatDateTime(s.last_attempted_sync_at)}>{timeAgo(s.last_attempted_sync_at)}</span>
                </Row>
              )}
              <Row label="Records">{s.record_count.toLocaleString()}</Row>
            </dl>
          </Card>

          {!isUpload && (
            <Card>
              <CardHeader
                title="Sign-in"
                action={
                  canSetCredentials &&
                  !removed &&
                  s.credentials.required.length > 0 && (
                    <Button
                      variant="secondary"
                      size="sm"
                      icon={<KeyRound className="size-3.5" />}
                      onClick={() => setPanel('credentials')}
                    >
                      {s.credentials.stored.length ? 'Update' : 'Add'}
                    </Button>
                  )
                }
              />
              <div className="space-y-3 px-5 py-4 text-sm">
                <p className="font-medium text-slate-900">{auth?.label}</p>
                {auth?.secret_fields.length ? (
                  <ul className="space-y-1.5">
                    {auth.secret_fields.map((field) => {
                      const stored = s.credentials.stored.includes(field.key)
                      return (
                        <li key={field.key} className="flex items-center justify-between gap-2">
                          <span className="text-slate-600">{field.label}</span>
                          <Badge tone={stored ? 'success' : 'warning'}>{stored ? 'Saved (hidden)' : 'Missing'}</Badge>
                        </li>
                      )
                    })}
                  </ul>
                ) : (
                  <p className="text-slate-500">The source is public; no credentials are needed.</p>
                )}
                {s.credentials.updated_at && (
                  <p className="text-xs text-slate-500">
                    Updated {timeAgo(s.credentials.updated_at).toLowerCase()}
                    {s.credentials.updated_by && ` by ${s.credentials.updated_by}`}
                  </p>
                )}
              </div>
            </Card>
          )}

          <Card>
            <CardHeader title="Settings" />
            <SettingsSummary catalog={catalog.data} source={s} />
          </Card>

          {canManage && !removed && (
            <Button
              variant="ghost"
              className="w-full text-rose-700 hover:bg-rose-50"
              icon={<Archive className="size-4" />}
              onClick={() => setPanel('remove')}
            >
              Remove source
            </Button>
          )}
          {removed && (
            <p className="text-center text-xs text-slate-500">
              Removed {formatDateTime(s.removed_at)}. Its records and history are kept permanently.
            </p>
          )}
        </div>
      </div>

      {panel === 'edit' && (
        <SourceDialog
          catalog={catalog.data}
          source={s}
          onClose={() => setPanel(null)}
          onSaved={(saved) => {
            setPanel(null)
            toast.success(
              !saved.credentials.complete && s.credentials.complete
                ? 'Saved. The site changed, so its credentials were cleared; add them again.'
                : 'Source saved',
            )
          }}
        />
      )}
      {panel === 'credentials' && (
        <CredentialsDialog catalog={catalog.data} source={s} onClose={() => setPanel(null)} />
      )}
      {panel === 'upload' && <UploadDialog catalog={catalog.data} source={s} onClose={() => setPanel(null)} />}
      <Dialog
        open={panel === 'remove'}
        onClose={() => setPanel(null)}
        title={`Remove ${s.name}?`}
        footer={
          <>
            <Button variant="secondary" onClick={() => setPanel(null)}>
              Cancel
            </Button>
            <Button
              variant="danger"
              loading={remove.isPending}
              onClick={() =>
                remove.mutate(undefined, {
                  onSuccess: () => {
                    toast.success(`Removed ${s.name}`)
                    navigate('/admin/sources')
                  },
                  onError: (error) => toast.error(errorMessage(error)),
                })
              }
            >
              Remove source
            </Button>
          </>
        }
      >
        <ul className="list-disc space-y-1.5 pl-5 text-sm text-slate-600">
          <li>It stops being fetched and disappears from the source list.</li>
          <li>Its stored credentials are deleted.</li>
          <li>
            Its <strong className="text-slate-900">{s.record_count.toLocaleString()} records</strong> and run
            history are kept permanently, so their origin stays traceable.
          </li>
          {active && <li>The fetch in progress is stopped.</li>}
        </ul>
      </Dialog>
      {run && (
        <RunDialog
          sourceId={s.id}
          jobId={run.id}
          onClose={() => setRun(null)}
          onShowRecords={
            canReadRecords
              ? () => {
                  setJobFilter({ id: run.id, label: `the ${jobTitle(run).toLowerCase()} ${timeAgo(run.created_at).toLowerCase()}` })
                  setRun(null)
                }
              : undefined
          }
        />
      )}
    </div>
  )
}
