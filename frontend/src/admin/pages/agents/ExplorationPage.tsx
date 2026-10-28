import { Play, ScanSearch, ShieldCheck } from 'lucide-react'
import { useState, type FormEvent } from 'react'
import { Link } from 'react-router'

import { Button } from '../../../components/ui/Button'
import { Alert, Badge, Card, CardHeader, EmptyState, PageHeader, Skeleton } from '../../../components/ui/Feedback'
import { TextField } from '../../../components/ui/Field'
import { useToast } from '../../../components/ui/Toast'
import { errorMessage } from '../../../lib/api'
import { cn } from '../../../lib/cn'
import { formatCount, formatUsd, timeAgo } from '../../../lib/format'
import type { AgentJob, ExplorationSource } from '../../../lib/types'
import { useCan } from '../../api'
import { useAgentStatus, useExplorationSources, useRecentRuns, useStartExploration } from '../../intelApi'
import { isActive, JobStatusBadge, TypeTile } from '../sources/shared'
import { AgentRunDialog, AiStatusBanner, runHeadline } from './shared'

function SourceRow({
  source,
  selected,
  onToggle,
  selectable,
}: {
  source: ExplorationSource
  selected: boolean
  onToggle: () => void
  selectable: boolean
}) {
  const blocked = !source.enabled ? 'Turned off' : source.active_job ? 'Busy' : null
  return (
    <li>
      <label
        className={cn(
          'flex items-start gap-3 px-5 py-3.5 transition',
          selectable && !blocked ? 'cursor-pointer hover:bg-slate-50' : 'opacity-70',
          selected && 'bg-brand-50/50',
        )}
      >
        <input
          type="checkbox"
          className="mt-3 size-4 accent-brand-600"
          checked={selected}
          disabled={!selectable || !!blocked}
          onChange={onToggle}
          aria-label={`Select ${source.name}`}
        />
        <TypeTile type={source.connector_type} className="size-9" />
        <span className="min-w-0 flex-1">
          <span className="flex flex-wrap items-center gap-2">
            <span className="font-medium text-slate-900">{source.name}</span>
            {blocked === 'Turned off' && <Badge>Off</Badge>}
            {source.active_job && <JobStatusBadge status={source.active_job.status} />}
          </span>
          <span className="mt-0.5 flex flex-wrap gap-x-4 gap-y-0.5 text-xs text-slate-500">
            <span>
              <strong className="font-semibold text-slate-800 tabular-nums">{formatCount(source.record_count)}</strong> records
            </span>
            <span>
              <strong
                className={cn('font-semibold tabular-nums', source.unexplored ? 'text-brand-700' : 'text-slate-800')}
              >
                {formatCount(source.unexplored)}
              </strong>{' '}
              not read yet
            </span>
            <span>
              <strong className="font-semibold text-slate-800 tabular-nums">{formatCount(source.questions)}</strong> questions
              {source.pending_review > 0 && ` (${source.pending_review} to review)`}
            </span>
            <span>Last explored {timeAgo(source.last_explored_at).toLowerCase()}</span>
          </span>
        </span>
      </label>
    </li>
  )
}

function RecentRuns({ onOpen }: { onOpen: (job: AgentJob) => void }) {
  const runs = useRecentRuns('exploration', 8)
  return (
    <Card className="overflow-hidden">
      <CardHeader
        title="Recent runs"
        description="Every run is kept with its log and cost."
        action={
          <Link to="/admin/agents/runs" className="text-sm font-semibold text-brand-700 hover:underline">
            All runs
          </Link>
        }
      />
      {runs.isPending ? (
        <div className="p-5">
          <Skeleton className="h-12" />
        </div>
      ) : runs.isError ? (
        <div className="p-5">
          <Alert>{errorMessage(runs.error)}</Alert>
        </div>
      ) : runs.data.items.length === 0 ? (
        <p className="px-5 py-6 text-sm text-slate-500">No exploration runs yet.</p>
      ) : (
        <ul className="divide-y divide-slate-100">
          {runs.data.items.map((job) => (
            <li key={job.id}>
              <button
                type="button"
                onClick={() => onOpen(job)}
                className="flex w-full flex-wrap items-center gap-x-3 gap-y-1 px-5 py-3 text-left transition hover:bg-slate-50"
              >
                <JobStatusBadge status={job.status} />
                <span className="min-w-0 flex-1">
                  <span className="block truncate text-sm font-medium text-slate-900">{job.source_name}</span>
                  <span className="block truncate text-xs text-slate-500">{runHeadline(job)}</span>
                  {isActive(job) && job.progress_total ? (
                    <span className="mt-1.5 block h-1.5 overflow-hidden rounded-full bg-slate-100">
                      <span
                        className="block h-full rounded-full bg-brand-500 transition-all"
                        style={{ width: `${Math.round((job.progress_done / job.progress_total) * 100)}%` }}
                      />
                    </span>
                  ) : null}
                </span>
                <span className="text-right text-xs text-slate-500">
                  {timeAgo(job.created_at)}
                  <span className="block tabular-nums">{formatUsd(job.cost_usd)}</span>
                </span>
              </button>
            </li>
          ))}
        </ul>
      )}
    </Card>
  )
}

export default function ExplorationPage() {
  const status = useAgentStatus()
  const sources = useExplorationSources()
  const canRun = useCan('agents.run')
  const start = useStartExploration()
  const toast = useToast()
  const [selected, setSelected] = useState<string[]>([])
  const [fetchFirst, setFetchFirst] = useState(true)
  const [maxRecords, setMaxRecords] = useState('50')
  const [maxCost, setMaxCost] = useState('1.00')
  const [openRun, setOpenRun] = useState<string | null>(null)

  const ready = !!status.data?.ai_configured
  const limitRecords = status.data?.max_records_per_run ?? 500
  const limitCost = Number(status.data?.max_cost_per_run_usd ?? 10)
  const recordsValue = Number(maxRecords)
  const costValue = Number(maxCost)
  const valid =
    selected.length > 0 &&
    Number.isInteger(recordsValue) &&
    recordsValue >= 1 &&
    recordsValue <= limitRecords &&
    costValue > 0 &&
    costValue <= limitCost

  const submit = (event: FormEvent) => {
    event.preventDefault()
    start.mutate(
      { source_ids: selected, fetch_first: fetchFirst, max_records: recordsValue, max_cost_usd: costValue.toFixed(2) },
      {
        onSuccess: (result) => {
          setSelected([])
          if (result.started.length) {
            toast.success(`Exploration started for ${result.started.length} source${result.started.length === 1 ? '' : 's'}`)
          }
          for (const skip of result.skipped) toast.error(`${skip.name ?? 'A source'}: ${skip.reason}`)
        },
        onError: (error) => toast.error(errorMessage(error)),
      },
    )
  }

  return (
    <div>
      <PageHeader
        title="Exploration agent"
        description="Reads interview records from your sources and extracts the questions for review. It never publishes anything."
      />
      <AiStatusBanner status={status.data} />

      <div className="grid items-start gap-5 lg:grid-cols-[minmax(0,1fr)_360px]">
        <Card className="overflow-hidden">
          <CardHeader
            title="Choose sources"
            description="Only records that haven't been read yet are sent to the AI, so a re-run never pays twice."
          />
          {sources.isPending ? (
            <div className="space-y-2 p-5">
              <Skeleton className="h-14" />
              <Skeleton className="h-14" />
            </div>
          ) : sources.isError ? (
            <div className="p-5">
              <Alert>{errorMessage(sources.error)}</Alert>
            </div>
          ) : sources.data.length === 0 ? (
            <EmptyState
              icon={<ScanSearch className="size-6" />}
              title="No sources yet"
              action={
                <Link to="/admin/sources" className="text-sm font-semibold text-brand-700 hover:underline">
                  Go to Interview sources
                </Link>
              }
            >
              Add an interview source and fetch or import its records first. The agent reads those records.
            </EmptyState>
          ) : (
            <ul className="divide-y divide-slate-100">
              {sources.data.map((source) => (
                <SourceRow
                  key={source.id}
                  source={source}
                  selectable={canRun}
                  selected={selected.includes(source.id)}
                  onToggle={() =>
                    setSelected((list) =>
                      list.includes(source.id) ? list.filter((id) => id !== source.id) : [...list, source.id],
                    )
                  }
                />
              ))}
            </ul>
          )}
        </Card>

        <div className="space-y-5">
          {canRun && (
            <Card>
              <CardHeader title="Run" />
              <form onSubmit={submit} className="space-y-4 p-5">
                <label className="flex cursor-pointer items-start gap-3">
                  <input
                    type="checkbox"
                    className="mt-0.5 size-4 accent-brand-600"
                    checked={fetchFirst}
                    onChange={(e) => setFetchFirst(e.target.checked)}
                  />
                  <span className="text-sm">
                    <span className="font-medium text-slate-900">Fetch new records first</span>
                    <span className="block text-xs text-slate-500">
                      For websites, APIs and feeds. File-import sources skip this step.
                    </span>
                  </span>
                </label>
                <div className="grid grid-cols-2 gap-3">
                  <TextField
                    label="Most records"
                    type="number"
                    min={1}
                    max={limitRecords}
                    value={maxRecords}
                    onChange={(e) => setMaxRecords(e.target.value)}
                    hint="Per source"
                  />
                  <TextField
                    label="Spending limit ($)"
                    type="number"
                    min={0.01}
                    max={limitCost}
                    step="0.01"
                    value={maxCost}
                    onChange={(e) => setMaxCost(e.target.value)}
                    hint="Per source"
                  />
                </div>
                <Button
                  type="submit"
                  className="w-full"
                  icon={<Play className="size-4" />}
                  loading={start.isPending}
                  disabled={!ready || !valid}
                  title={!ready ? 'Connect the AI provider first' : undefined}
                >
                  {selected.length ? `Run on ${selected.length} source${selected.length === 1 ? '' : 's'}` : 'Select sources to run'}
                </Button>
                {status.data && (
                  <p className="text-xs text-slate-500">
                    Model: <span className="font-mono">{status.data.extraction_model}</span>. One AI call per record;
                    the run stops at the spending limit.
                  </p>
                )}
              </form>
            </Card>
          )}

          <Card className="p-5">
            <h2 className="mb-3 flex items-center gap-2 font-display text-base font-semibold text-slate-900">
              <ShieldCheck className="size-4 text-emerald-600" aria-hidden /> Safeguards
            </h2>
            <ul className="space-y-2 text-sm text-slate-600">
              <li>Questions are copied as written. Any not found word-for-word in the record are flagged.</li>
              <li>A company is only kept if the record names it; nothing is inferred.</li>
              <li>
                Everything waits in{' '}
                <Link to="/admin/intelligence" className="font-semibold text-brand-700 hover:underline">
                  Interview intelligence
                </Link>{' '}
                until a reviewer approves it.
              </li>
            </ul>
          </Card>
        </div>
      </div>

      <div className="mt-5">
        <RecentRuns onOpen={(job) => setOpenRun(job.id)} />
      </div>
      {openRun && <AgentRunDialog jobId={openRun} onClose={() => setOpenRun(null)} />}
    </div>
  )
}
