import { Database, Play, Plus } from 'lucide-react'
import { useState } from 'react'
import { Link, useNavigate } from 'react-router'

import { Button } from '../../../components/ui/Button'
import { Alert, Badge, Card, EmptyState, PageHeader, Skeleton } from '../../../components/ui/Feedback'
import { useToast } from '../../../components/ui/Toast'
import { errorMessage } from '../../../lib/api'
import { cn } from '../../../lib/cn'
import { formatCount, timeAgo } from '../../../lib/format'
import type { SourceListItem } from '../../../lib/types'
import { useCan, useFetchSources, useSourceCatalog, useSources } from '../../api'
import { ConnectionBadge, hostOf, JobStatusBadge, TypeTile } from './shared'
import { SourceDialog } from './SourceDialog'

function SourceCard({
  source,
  typeLabel,
  selectable,
  selected,
  onSelect,
}: {
  source: SourceListItem
  typeLabel: string
  selectable: boolean
  selected: boolean
  onSelect: (selected: boolean) => void
}) {
  const removed = !!source.removed_at
  return (
    <Card
      className={cn(
        'relative flex gap-3 p-4 transition hover:shadow-md hover:ring-slate-300',
        selected && 'ring-2 ring-brand-400 hover:ring-brand-400',
        (removed || !source.enabled) && 'opacity-75',
      )}
    >
      {selectable && (
        <input
          type="checkbox"
          className="relative z-10 mt-3 size-4 accent-brand-600"
          checked={selected}
          onChange={(e) => onSelect(e.target.checked)}
          aria-label={`Select ${source.name}`}
        />
      )}
      <TypeTile type={source.connector_type} />
      <div className="min-w-0 flex-1">
        <div className="flex flex-wrap items-start justify-between gap-2">
          <div className="min-w-0">
            <Link
              to={`/admin/sources/${source.id}`}
              className="font-semibold text-slate-900 after:absolute after:inset-0 after:rounded-2xl hover:text-brand-700"
            >
              {source.name}
            </Link>
            <p className="truncate text-xs text-slate-500">
              {typeLabel}
              {source.base_url && ` · ${hostOf(source.base_url)}`}
            </p>
          </div>
          <div className="flex flex-wrap gap-1">
            {removed ? (
              <Badge>Removed</Badge>
            ) : !source.enabled ? (
              <Badge>Off</Badge>
            ) : source.active_job ? (
              <JobStatusBadge status={source.active_job.status} />
            ) : (
              <ConnectionBadge status={source.connection_status} />
            )}
            {!removed && !source.credentials.complete && <Badge tone="warning">Needs credentials</Badge>}
          </div>
        </div>
        <p className="mt-3 flex flex-wrap gap-x-4 gap-y-1 text-xs text-slate-600">
          <span>
            <span className="font-semibold text-slate-900 tabular-nums">{formatCount(source.record_count)}</span>{' '}
            record{source.record_count === 1 ? '' : 's'}
          </span>
          <span>
            Last fetched{' '}
            <span className="font-medium text-slate-900">{timeAgo(source.last_successful_sync_at).toLowerCase()}</span>
          </span>
          {source.active_job && (
            <span className="font-medium text-brand-700">{source.active_job.progress_done} saved so far</span>
          )}
        </p>
      </div>
    </Card>
  )
}

export default function SourcesPage() {
  const [showRemoved, setShowRemoved] = useState(false)
  const sources = useSources(showRemoved)
  const catalog = useSourceCatalog()
  const canManage = useCan('sources.manage')
  const [adding, setAdding] = useState(false)
  const [selected, setSelected] = useState<string[]>([])
  const fetchMany = useFetchSources()
  const toast = useToast()
  const navigate = useNavigate()

  const labels = Object.fromEntries((catalog.data?.connectors ?? []).map((c) => [c.key, c.label]))
  const fetchable = (s: SourceListItem) =>
    !s.removed_at && s.enabled && s.connector_type !== 'file_upload' && !s.active_job
  const selectedFetchable = (sources.data ?? []).filter((s) => selected.includes(s.id) && fetchable(s))

  const fetchSelected = () =>
    fetchMany.mutate(
      selectedFetchable.map((s) => s.id),
      {
        onSuccess: (result) => {
          setSelected([])
          if (result.started.length) toast.success(`Started ${result.started.length} fetch${result.started.length === 1 ? '' : 'es'}`)
          for (const skip of result.skipped) toast.error(`${skip.name ?? 'A source'}: ${skip.reason}`)
        },
        onError: (error) => toast.error(errorMessage(error)),
      },
    )

  return (
    <div>
      <PageHeader
        title="Interview sources"
        description="Where interview experiences come from. Nothing is fetched until someone presses Fetch."
        actions={
          canManage && (
            <Button icon={<Plus className="size-4" />} onClick={() => setAdding(true)} disabled={!catalog.data}>
              Add source
            </Button>
          )
        }
      />

      {catalog.data && !catalog.data.credential_storage_ready && (
        <Alert className="mb-5">
          Credential storage isn't set up on the server (IPP_CREDENTIALS_KEYS). Public sources and
          file imports work; sources that need a sign-in can't store credentials until it is.
        </Alert>
      )}

      {canManage && selected.length > 0 && (
        <div className="sticky top-16 z-10 mb-4 flex flex-wrap items-center gap-3 rounded-2xl bg-slate-900 px-4 py-3 text-sm text-white shadow-lg lg:top-4">
          <span>
            {selected.length} selected
            {selectedFetchable.length < selected.length && (
              <span className="text-slate-400"> · {selected.length - selectedFetchable.length} can't be fetched now</span>
            )}
          </span>
          <div className="ml-auto flex gap-2">
            <Button variant="ghost" size="sm" className="text-slate-300 hover:bg-white/10 hover:text-white" onClick={() => setSelected([])}>
              Clear
            </Button>
            <Button
              size="sm"
              icon={<Play className="size-3.5" />}
              loading={fetchMany.isPending}
              disabled={!selectedFetchable.length}
              onClick={fetchSelected}
            >
              Fetch {selectedFetchable.length || ''}
            </Button>
          </div>
        </div>
      )}

      {sources.isPending ? (
        <div className="grid gap-3 md:grid-cols-2">
          <Skeleton className="h-28 rounded-2xl" />
          <Skeleton className="h-28 rounded-2xl" />
        </div>
      ) : sources.isError ? (
        <Alert>{errorMessage(sources.error)}</Alert>
      ) : sources.data.length === 0 ? (
        <Card>
          <EmptyState
            icon={<Database className="size-6" />}
            title={showRemoved ? 'No sources' : 'No sources yet'}
            action={
              canManage && (
                <Button icon={<Plus className="size-4" />} onClick={() => setAdding(true)} disabled={!catalog.data}>
                  Add your first source
                </Button>
              )
            }
          >
            Add a website, a data API, an RSS feed, or a place to import files. Credentials are
            stored encrypted and nothing runs until you ask.
          </EmptyState>
        </Card>
      ) : (
        <div className="grid gap-3 md:grid-cols-2">
          {sources.data.map((source) => (
            <SourceCard
              key={source.id}
              source={source}
              typeLabel={labels[source.connector_type] ?? source.connector_type}
              selectable={canManage && fetchable(source)}
              selected={selected.includes(source.id)}
              onSelect={(on) =>
                setSelected((list) => (on ? [...list, source.id] : list.filter((id) => id !== source.id)))
              }
            />
          ))}
        </div>
      )}

      <label className="mt-5 inline-flex cursor-pointer items-center gap-2 text-sm text-slate-600">
        <input
          type="checkbox"
          className="size-4 accent-brand-600"
          checked={showRemoved}
          onChange={(e) => {
            setShowRemoved(e.target.checked)
            setSelected([])
          }}
        />
        Show removed sources
      </label>

      {adding && catalog.data && (
        <SourceDialog
          catalog={catalog.data}
          source={null}
          onClose={() => setAdding(false)}
          onSaved={(saved) => {
            toast.success(
              saved.credentials.complete ? `Added ${saved.name}` : `Added ${saved.name}. Add its credentials next.`,
            )
            navigate(`/admin/sources/${saved.id}`)
          }}
        />
      )}
    </div>
  )
}
