import { Plus, Telescope, X } from 'lucide-react'
import { useState, type FormEvent } from 'react'
import { Link } from 'react-router'

import { Pagination } from '../../../components/Pagination'
import { Button } from '../../../components/ui/Button'
import { Alert, Badge, Card, CardHeader, EmptyState, PageHeader, Skeleton } from '../../../components/ui/Feedback'
import { SelectField, TextField } from '../../../components/ui/Field'
import { useToast } from '../../../components/ui/Toast'
import { errorMessage } from '../../../lib/api'
import { cn } from '../../../lib/cn'
import { formatDate, timeAgo } from '../../../lib/format'
import type { AgentJob } from '../../../lib/types'
import { useCan } from '../../api'
import { useAgentStatus, useRecentRuns, useRecommendations, useReports, useStartResearch } from '../../intelApi'
import { isActive, JobStatusBadge } from '../sources/shared'
import { RecommendationCard } from './RecommendationCard'
import { AgentRunDialog, AiStatusBanner, runHeadline } from './shared'

const REGIONS = ['Global', 'India', 'United States', 'United Kingdom', 'Europe', 'Southeast Asia', 'Middle East']

function ResearchForm({ presets, ready, model, engine }: { presets: string[]; ready: boolean; model: string; engine: string }) {
  const start = useStartResearch()
  const toast = useToast()
  const [roles, setRoles] = useState<string[]>(presets.slice(0, 2))
  const [custom, setCustom] = useState('')
  const [focus, setFocus] = useState('')
  const [region, setRegion] = useState('India')
  const [months, setMonths] = useState('6')
  const [perSearch, setPerSearch] = useState('5')
  const [maxCost, setMaxCost] = useState('0.50')
  const choices = [...new Set([...presets, ...roles])]

  const toggle = (role: string) =>
    setRoles((list) => (list.includes(role) ? list.filter((r) => r !== role) : list.length < 6 ? [...list, role] : list))

  const submit = (event: FormEvent) => {
    event.preventDefault()
    start.mutate(
      {
        roles,
        focus: focus.trim(),
        region,
        months: Number(months),
        sources_per_search: Number(perSearch),
        max_cost_usd: Number(maxCost).toFixed(2),
      },
      {
        onSuccess: () => toast.success('Research started. The report appears below when it finishes.'),
        onError: (e) => toast.error(errorMessage(e)),
      },
    )
  }

  return (
    <form onSubmit={submit} className="space-y-4 p-5">
      <fieldset>
        <legend className="mb-2 text-sm font-medium text-slate-800">Roles (up to 6)</legend>
        <div className="flex flex-wrap gap-1.5">
          {choices.map((role) => {
            const on = roles.includes(role)
            return (
              <button
                key={role}
                type="button"
                aria-pressed={on}
                onClick={() => toggle(role)}
                className={cn(
                  'inline-flex items-center gap-1 rounded-full px-3 py-1 text-xs font-medium ring-1 transition',
                  on ? 'bg-brand-600 text-white ring-brand-600' : 'bg-white text-slate-700 ring-slate-300 hover:ring-slate-400',
                )}
              >
                {role}
                {on && <X className="size-3" aria-hidden />}
              </button>
            )
          })}
        </div>
        <div className="mt-2 flex gap-2">
          <input
            value={custom}
            onChange={(e) => setCustom(e.target.value)}
            placeholder="Another role"
            maxLength={80}
            aria-label="Another role"
            className="min-w-0 flex-1 rounded-xl border-0 px-3 py-2 text-sm ring-1 ring-slate-300 ring-inset focus:ring-2 focus:ring-brand-500 focus:outline-none"
          />
          <Button
            variant="secondary"
            size="sm"
            icon={<Plus className="size-3.5" />}
            disabled={custom.trim().length < 2 || roles.length >= 6}
            onClick={() => {
              const role = custom.trim()
              if (!roles.includes(role)) setRoles((list) => [...list, role])
              setCustom('')
            }}
          >
            Add
          </Button>
        </div>
      </fieldset>
      <TextField
        label="Focus (optional)"
        value={focus}
        onChange={(e) => setFocus(e.target.value)}
        placeholder="e.g. Agentic AI, LLM evaluation"
        maxLength={200}
      />
      <div className="grid grid-cols-2 gap-3">
        <SelectField label="Region" value={region} onChange={(e) => setRegion(e.target.value)}>
          {REGIONS.map((r) => (
            <option key={r}>{r}</option>
          ))}
        </SelectField>
        <SelectField label="Time window" value={months} onChange={(e) => setMonths(e.target.value)}>
          <option value="3">3 months</option>
          <option value="6">6 months</option>
          <option value="12">12 months</option>
        </SelectField>
        <SelectField label="Sources per search" value={perSearch} onChange={(e) => setPerSearch(e.target.value)}>
          {[3, 5, 8, 10].map((n) => (
            <option key={n} value={n}>
              {n}
            </option>
          ))}
        </SelectField>
        <TextField
          label="Spending limit ($)"
          type="number"
          min={0.05}
          step="0.05"
          value={maxCost}
          onChange={(e) => setMaxCost(e.target.value)}
        />
      </div>
      <Button
        type="submit"
        className="w-full"
        icon={<Telescope className="size-4" />}
        loading={start.isPending}
        disabled={!ready || roles.length === 0 || !(Number(maxCost) > 0)}
        title={!ready ? 'Connect the AI provider first' : undefined}
      >
        Start research
      </Button>
      <p className="text-xs text-slate-500">
        One web search per role with <span className="font-mono">{model}</span> ({engine} search), then one call to write
        the report. Web searches are billed per search on top of model tokens; the run stops at the spending limit.
      </p>
    </form>
  )
}

function ActiveRuns({ onOpen }: { onOpen: (job: AgentJob) => void }) {
  const runs = useRecentRuns('market_research')
  const shown = (runs.data?.items ?? []).filter((job) => isActive(job) || job.status === 'failed').slice(0, 3)
  if (!shown.length) return null
  return (
    <Card className="overflow-hidden">
      <CardHeader title="Recent research runs" />
      <ul className="divide-y divide-slate-100">
        {shown.map((job) => (
          <li key={job.id}>
            <button type="button" onClick={() => onOpen(job)} className="flex w-full items-center gap-3 px-5 py-3 text-left hover:bg-slate-50">
              <JobStatusBadge status={job.status} />
              <span className="min-w-0 flex-1 truncate text-sm text-slate-700">{runHeadline(job)}</span>
              <span className="text-xs text-slate-500">{timeAgo(job.created_at)}</span>
            </button>
          </li>
        ))}
      </ul>
    </Card>
  )
}

export default function ResearchPage() {
  const status = useAgentStatus()
  const canRun = useCan('agents.run')
  const recommendations = useRecommendations()
  const [page, setPage] = useState(1)
  const reports = useReports(page)
  const [openRun, setOpenRun] = useState<string | null>(null)

  return (
    <div>
      <PageHeader
        title="Market research"
        description="Cited research on what AI/ML employers want now. It recommends; people decide, and nothing is generated."
      />
      <AiStatusBanner status={status.data} />

      <div className="grid items-start gap-5 lg:grid-cols-[360px_minmax(0,1fr)]">
        <div className="space-y-5">
          {canRun && status.data && (
            <Card>
              <CardHeader title="New research" />
              <ResearchForm
                presets={status.data.role_presets}
                ready={status.data.ai_configured}
                model={status.data.research_model}
                engine={status.data.search_engine}
              />
            </Card>
          )}
          <ActiveRuns onOpen={(job) => setOpenRun(job.id)} />
        </div>

        <div className="min-w-0 space-y-5">
          <Card>
            <CardHeader
              title="Waiting for a decision"
              description="Curriculum recommendations from research. Approving never generates content."
            />
            <div className="space-y-3 p-5">
              {recommendations.isPending ? (
                <Skeleton className="h-20" />
              ) : recommendations.isError ? (
                <Alert>{errorMessage(recommendations.error)}</Alert>
              ) : recommendations.data.length === 0 ? (
                <p className="text-sm text-slate-500">No recommendations are waiting.</p>
              ) : (
                recommendations.data.map((rec) => <RecommendationCard key={rec.id} rec={rec} />)
              )}
            </div>
          </Card>

          <Card className="overflow-hidden">
            <CardHeader title="Reports" description="Every claim in a report cites the page it came from." />
            {reports.isPending ? (
              <div className="p-5">
                <Skeleton className="h-24" />
              </div>
            ) : reports.isError ? (
              <div className="p-5">
                <Alert>{errorMessage(reports.error)}</Alert>
              </div>
            ) : reports.data.items.length === 0 ? (
              <EmptyState icon={<Telescope className="size-6" />} title="No research yet">
                Start research on the roles you prepare students for. Reports list their sources and findings.
              </EmptyState>
            ) : (
              <>
                <ul className="divide-y divide-slate-100">
                  {reports.data.items.map((report) => (
                    <li key={report.id}>
                      <Link to={`/admin/agents/research/${report.id}`} className="block px-5 py-4 transition hover:bg-slate-50">
                        <div className="flex flex-wrap items-start justify-between gap-2">
                          <p className="font-medium text-slate-900">{report.title}</p>
                          <span className="text-xs text-slate-500">{formatDate(report.created_at)}</span>
                        </div>
                        <div className="mt-1.5 flex flex-wrap gap-1">
                          {report.scope.roles.map((r) => (
                            <Badge key={r}>{r}</Badge>
                          ))}
                          <Badge>{report.scope.region}</Badge>
                          <Badge>Last {report.scope.months} months</Badge>
                        </div>
                        <p className="mt-2 text-xs text-slate-500">
                          {report.findings} findings from {report.sources} sources · {report.questions} practice questions
                          {report.pending_recommendations > 0 && (
                            <span className="font-semibold text-amber-700"> · {report.pending_recommendations} to decide</span>
                          )}
                        </p>
                      </Link>
                    </li>
                  ))}
                </ul>
                {reports.data.total > 10 && <Pagination page={page} pageSize={10} total={reports.data.total} onPage={setPage} />}
              </>
            )}
          </Card>
        </div>
      </div>
      {openRun && <AgentRunDialog jobId={openRun} onClose={() => setOpenRun(null)} />}
    </div>
  )
}
