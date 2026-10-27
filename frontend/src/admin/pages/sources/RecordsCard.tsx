import { ExternalLink, FileText, Search, ShieldAlert, X } from 'lucide-react'
import { useEffect, useState } from 'react'

import { Pagination } from '../../../components/Pagination'
import { Dialog } from '../../../components/ui/Dialog'
import { Alert, Badge, Card, EmptyState, Skeleton } from '../../../components/ui/Feedback'
import { errorMessage } from '../../../lib/api'
import { formatCount, formatDateTime, timeAgo } from '../../../lib/format'
import { useSourceRecord, useSourceRecords } from '../../api'

function RecordDialog({ sourceId, recordId, onClose }: { sourceId: string; recordId: number; onClose: () => void }) {
  const record = useSourceRecord(sourceId, recordId)
  const data = record.data
  return (
    <Dialog
      open
      onClose={onClose}
      size="lg"
      title={data ? (data.title ?? data.external_id) : 'Record'}
      description="Raw source text, exactly as fetched. Admin-only: students never see raw records."
    >
      {record.isPending ? (
        <Skeleton className="h-64" />
      ) : record.isError ? (
        <Alert>{errorMessage(record.error)}</Alert>
      ) : (
        <div className="space-y-4">
          <dl className="grid gap-x-4 gap-y-2 text-sm sm:grid-cols-2">
            <div>
              <dt className="text-xs text-slate-500">Fetched</dt>
              <dd className="text-slate-900">{formatDateTime(record.data.fetched_at)}</dd>
            </div>
            <div>
              <dt className="text-xs text-slate-500">Revision</dt>
              <dd className="text-slate-900">
                {record.data.revision}
                {record.data.revision > 1 && ' (the source changed it; earlier versions are kept)'}
              </dd>
            </div>
            {record.data.published_at && (
              <div>
                <dt className="text-xs text-slate-500">Published</dt>
                <dd className="text-slate-900">{formatDateTime(record.data.published_at)}</dd>
              </div>
            )}
            <div className="min-w-0 sm:col-span-2">
              <dt className="text-xs text-slate-500">Source ID</dt>
              <dd className="font-mono text-xs break-all text-slate-700">{record.data.external_id}</dd>
            </div>
            {record.data.url && (
              <div className="min-w-0 sm:col-span-2">
                <dt className="text-xs text-slate-500">Link</dt>
                <dd>
                  <a
                    href={record.data.url}
                    target="_blank"
                    rel="noreferrer noopener"
                    className="inline-flex max-w-full items-center gap-1 text-sm font-medium break-all text-brand-700 hover:underline"
                  >
                    {record.data.url}
                    <ExternalLink className="size-3.5 shrink-0" aria-hidden />
                  </a>
                </dd>
              </div>
            )}
          </dl>
          <pre className="max-h-[45dvh] overflow-auto rounded-xl bg-slate-50 p-4 text-xs leading-relaxed whitespace-pre-wrap text-slate-800 ring-1 ring-slate-200">
            {record.data.content}
          </pre>
        </div>
      )}
    </Dialog>
  )
}

export function RecordsCard({
  sourceId,
  jobFilter,
  onClearJobFilter,
}: {
  sourceId: string
  jobFilter: { id: string; label: string } | null
  onClearJobFilter: () => void
}) {
  const [search, setSearch] = useState('')
  const [q, setQ] = useState('')
  const [page, setPage] = useState(1)
  const [open, setOpen] = useState<number | null>(null)
  const records = useSourceRecords(sourceId, { q, jobId: jobFilter?.id ?? null, page }, true)

  useEffect(() => {
    const timer = window.setTimeout(() => {
      setQ(search)
      setPage(1)
    }, 300)
    return () => window.clearTimeout(timer)
  }, [search])
  useEffect(() => setPage(1), [jobFilter?.id])

  return (
    <Card className="overflow-hidden">
      <div className="flex flex-wrap items-center justify-between gap-3 border-b border-slate-100 px-5 py-4">
        <div>
          <h2 className="font-display text-base font-semibold text-slate-900">Records</h2>
          <p className="flex items-center gap-1 text-sm text-slate-500">
            <ShieldAlert className="size-3.5" aria-hidden /> Raw text, admin-only. Kept permanently.
          </p>
        </div>
        <label className="relative w-full sm:w-64">
          <span className="sr-only">Search records</span>
          <Search className="pointer-events-none absolute top-1/2 left-3 size-4 -translate-y-1/2 text-slate-400" aria-hidden />
          <input
            type="search"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Search titles and links"
            className="w-full rounded-xl border-0 bg-white py-2 pr-3 pl-9 text-sm ring-1 ring-slate-300 ring-inset focus:ring-2 focus:ring-brand-500 focus:outline-none"
          />
        </label>
      </div>
      {jobFilter && (
        <div className="flex items-center gap-2 border-b border-slate-100 bg-brand-50/50 px-5 py-2 text-sm text-brand-900">
          Showing records from {jobFilter.label}
          <button
            type="button"
            onClick={onClearJobFilter}
            className="ml-auto inline-flex items-center gap-1 rounded-md px-1.5 py-0.5 text-xs font-semibold hover:bg-brand-100"
          >
            <X className="size-3.5" aria-hidden /> Show all
          </button>
        </div>
      )}
      {records.isPending ? (
        <div className="space-y-2 p-5">
          <Skeleton className="h-12" />
          <Skeleton className="h-12" />
        </div>
      ) : records.isError ? (
        <div className="p-5">
          <Alert>{errorMessage(records.error)}</Alert>
        </div>
      ) : records.data.items.length === 0 ? (
        <EmptyState icon={<FileText className="size-6" />} title={q || jobFilter ? 'No matching records' : 'No records yet'}>
          {q || jobFilter ? 'Try a different search.' : 'Fetch the source or import files to add records.'}
        </EmptyState>
      ) : (
        <>
          <ul className="divide-y divide-slate-100">
            {records.data.items.map((record) => (
              <li key={record.id}>
                <button
                  type="button"
                  onClick={() => setOpen(record.id)}
                  className="flex w-full items-start gap-3 px-5 py-3 text-left transition hover:bg-slate-50"
                >
                  <FileText className="mt-0.5 size-4 shrink-0 text-slate-400" aria-hidden />
                  <span className="min-w-0 flex-1">
                    <span className="block truncate text-sm font-medium text-slate-900">
                      {record.title ?? record.external_id}
                    </span>
                    <span className="block truncate text-xs text-slate-500">
                      {record.url ?? record.external_id}
                    </span>
                  </span>
                  <span className="hidden shrink-0 flex-col items-end gap-1 sm:flex">
                    <span className="text-xs text-slate-500">{timeAgo(record.fetched_at)}</span>
                    <span className="flex gap-1">
                      {record.revision > 1 && <Badge tone="warning">Rev {record.revision}</Badge>}
                      <Badge>{formatCount(record.content_length)} chars</Badge>
                    </span>
                  </span>
                </button>
              </li>
            ))}
          </ul>
          {records.data.total > 10 && (
            <Pagination page={page} pageSize={10} total={records.data.total} onPage={setPage} />
          )}
        </>
      )}
      {open !== null && <RecordDialog sourceId={sourceId} recordId={open} onClose={() => setOpen(null)} />}
    </Card>
  )
}
