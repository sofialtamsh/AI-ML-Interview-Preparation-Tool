import { FolderTree, LockKeyhole, LockKeyholeOpen, Sparkles, Wand2 } from 'lucide-react'
import { useState } from 'react'
import { Link } from 'react-router'

import { Button, ButtonLink } from '../../../components/ui/Button'
import { Dialog } from '../../../components/ui/Dialog'
import { Alert, Badge, Card, CardHeader, PageHeader, Skeleton } from '../../../components/ui/Feedback'
import { TextField } from '../../../components/ui/Field'
import { useToast } from '../../../components/ui/Toast'
import { SECTION_ORDER, SECTIONS } from '../../../learn/sections'
import { errorMessage } from '../../../lib/api'
import { cn } from '../../../lib/cn'
import type { ContentComponent, ContentOverview } from '../../../lib/types'
import { useCan } from '../../api'
import { useContentOverview, useGenerate, useSetExpansion } from '../../contentApi'
import { ContentRuns, VERSION_STATUS } from './shared'

export default function ContentStudioPage() {
  const overview = useContentOverview()
  const canGenerate = useCan('content.generate')

  return (
    <div className="space-y-6">
      <PageHeader
        title="Content studio"
        description="Review, edit and publish learning content. Students only ever see what you publish."
        actions={
          <ButtonLink to="/admin/topics" variant="secondary">
            <FolderTree className="size-4" aria-hidden /> Domains & topics
          </ButtonLink>
        }
      />

      {overview.isPending && <Skeleton className="h-64 rounded-2xl" />}
      {overview.isError && <Alert>{errorMessage(overview.error)}</Alert>}
      {overview.data && (
        <>
          <GateCard overview={overview.data} />
          {!overview.data.ai_configured && (
            <Alert tone="info">
              The AI provider isn&apos;t connected, so generation and narration are off. Starter drafts can still be
              reviewed, edited and published. Add <code className="rounded bg-white/70 px-1 text-xs">IPP_OPENROUTER_API_KEY</code>{' '}
              to <code className="text-xs">backend/.env</code> and restart the API to turn them on.
            </Alert>
          )}
          <TopicGrid overview={overview.data} />
          {canGenerate && <GeneratePanel overview={overview.data} />}
        </>
      )}

      <Card className="overflow-hidden">
        <CardHeader title="Recent runs" description="Generation and narration jobs. Click one for its log." />
        <ContentRuns />
      </Card>
    </div>
  )
}

function GateCard({ overview }: { overview: ContentOverview }) {
  const canDecide = useCan('settings.manage')
  const setExpansion = useSetExpansion()
  const toast = useToast()
  const [confirming, setConfirming] = useState(false)
  const pilots = overview.topics.filter((t) => t.topic.is_pilot).length
  const approved = overview.expansion_approved

  return (
    <Card className="flex flex-wrap items-center gap-4 p-5">
      <span className={cn('grid size-11 place-items-center rounded-2xl', approved ? 'bg-emerald-50 text-emerald-600' : 'bg-amber-50 text-amber-600')}>
        {approved ? <LockKeyholeOpen className="size-5" /> : <LockKeyhole className="size-5" />}
      </span>
      <div className="min-w-0 flex-1">
        <p className="flex flex-wrap items-center gap-2 font-semibold text-slate-900">
          Generation gate {approved ? <Badge tone="success">Expansion approved</Badge> : <Badge tone="warning">Pilot only</Badge>}
        </p>
        <p className="text-sm text-slate-600">
          {approved
            ? 'Content can be generated for every topic. Publishing still needs review.'
            : `AI generation is limited to the ${pilots} pilot topics until an admin approves expansion.`}
        </p>
      </div>
      {canDecide ? (
        <Button variant={approved ? 'secondary' : 'primary'} onClick={() => setConfirming(true)}>
          {approved ? 'Return to pilot only' : 'Approve expansion'}
        </Button>
      ) : (
        <p className="text-xs text-slate-500">Changing this needs the settings permission.</p>
      )}
      <Dialog
        open={confirming}
        onClose={() => setConfirming(false)}
        title={approved ? 'Return to pilot only?' : 'Approve content expansion?'}
        description={
          approved
            ? 'New generation will again be limited to pilot topics. Existing content is untouched.'
            : 'Admins with the generate permission will be able to generate drafts for any topic. Nothing is published without review.'
        }
        footer={
          <>
            <Button variant="secondary" onClick={() => setConfirming(false)}>
              Cancel
            </Button>
            <Button
              loading={setExpansion.isPending}
              onClick={() =>
                setExpansion.mutate(!approved, {
                  onSuccess: () => {
                    toast.success(approved ? 'Generation is back to pilot topics only' : 'Expansion approved')
                    setConfirming(false)
                  },
                  onError: (error) => toast.error(errorMessage(error)),
                })
              }
            >
              {approved ? 'Return to pilot only' : 'Approve expansion'}
            </Button>
          </>
        }
      >
        <p className="text-sm text-slate-600">This decision is recorded in the audit log.</p>
      </Dialog>
    </Card>
  )
}

function TopicGrid({ overview }: { overview: ContentOverview }) {
  return (
    <Card className="overflow-hidden">
      <CardHeader title="Topics" description="Latest version of each component. A green ring means students can see it." />
      <ul className="grid gap-px bg-slate-100 sm:grid-cols-2">
        {overview.topics.map(({ topic, statuses, live, published }) => (
          <li key={topic.id} className="bg-white">
            <Link to={`/admin/content/${topic.id}`} className="block h-full p-5 transition hover:bg-slate-50">
              <div className="flex items-start justify-between gap-3">
                <div className="min-w-0">
                  <p className="text-xs text-slate-500">{topic.domain_name}</p>
                  <p className="font-semibold text-slate-900">{topic.name}</p>
                </div>
                <div className="flex shrink-0 flex-col items-end gap-1">
                  {topic.is_pilot && <Badge tone="brand">Pilot</Badge>}
                  <span className="text-xs text-slate-500 tabular-nums">{published}/7 live</span>
                </div>
              </div>
              <ul className="mt-3 flex flex-wrap gap-1.5">
                {SECTION_ORDER.map((component) => {
                  const status = statuses[component]
                  const isLive = live.includes(component)
                  const meta = status ? VERSION_STATUS[status] : null
                  return (
                    <li
                      key={component}
                      title={`${SECTIONS[component].admin}: ${meta?.label ?? 'No content'}${isLive ? ' (live)' : ''}`}
                      className={cn(
                        'inline-flex items-center gap-1 rounded-full bg-slate-50 px-2 py-0.5 text-xs text-slate-700 ring-1',
                        isLive ? 'ring-2 ring-emerald-400' : 'ring-slate-200',
                      )}
                    >
                      <span className={cn('size-1.5 rounded-full', meta?.dot ?? 'bg-slate-200')} aria-hidden />
                      {SECTIONS[component].label}
                      <span className="sr-only">: {meta?.label ?? 'no content'}{isLive ? ', live' : ''}</span>
                    </li>
                  )
                })}
              </ul>
            </Link>
          </li>
        ))}
      </ul>
      <ul className="flex flex-wrap gap-x-4 gap-y-1 border-t border-slate-100 px-5 py-3 text-xs text-slate-600">
        {Object.entries(VERSION_STATUS).map(([key, meta]) => (
          <li key={key} className="inline-flex items-center gap-1.5">
            <span className={cn('size-1.5 rounded-full', meta.dot)} aria-hidden />
            {meta.label}
          </li>
        ))}
        <li className="inline-flex items-center gap-1.5">
          <span className="size-2.5 rounded-full ring-2 ring-emerald-400" aria-hidden />
          Live for students
        </li>
      </ul>
    </Card>
  )
}

function GeneratePanel({ overview }: { overview: ContentOverview }) {
  const generate = useGenerate()
  const toast = useToast()
  const eligible = overview.topics.filter((t) => t.may_generate)
  const [topics, setTopics] = useState<string[]>([])
  const [components, setComponents] = useState<ContentComponent[]>([...SECTION_ORDER])
  const [useIntelligence, setUseIntelligence] = useState(true)
  const [limit, setLimit] = useState('2')
  const [skipped, setSkipped] = useState<{ name: string | null; reason: string }[]>([])

  const toggle = <T,>(list: T[], value: T) => (list.includes(value) ? list.filter((v) => v !== value) : [...list, value])
  const limitValue = Number(limit)
  const limitOk = Number.isFinite(limitValue) && limitValue > 0 && limitValue <= 100
  const ready = overview.ai_configured && topics.length > 0 && components.length > 0 && limitOk

  const submit = () =>
    generate.mutate(
      { topic_ids: topics, components, use_intelligence: useIntelligence, max_cost_usd: limit },
      {
        onSuccess: (result) => {
          setSkipped(result.skipped)
          if (result.started.length) toast.success(`Started ${result.started.length} generation run(s). Drafts arrive for review.`)
          setTopics([])
        },
        onError: (error) => toast.error(errorMessage(error)),
      },
    )

  return (
    <Card>
      <CardHeader
        title="Generate drafts"
        description={`New versions arrive as drafts for review; nothing is published automatically. Model: ${overview.content_model}.`}
      />
      <div className="space-y-5 p-5">
        <fieldset>
          <legend className="text-sm font-semibold text-slate-900">Topics</legend>
          <div className="mt-2 flex flex-wrap gap-2">
            {overview.topics.map(({ topic, may_generate }) => (
              <label
                key={topic.id}
                className={cn(
                  'inline-flex items-center gap-2 rounded-xl px-3 py-1.5 text-sm ring-1 ring-inset',
                  may_generate ? 'cursor-pointer ring-slate-200 hover:bg-slate-50' : 'cursor-not-allowed text-slate-400 ring-slate-100',
                  topics.includes(topic.id) && 'bg-brand-50 ring-brand-300',
                )}
                title={may_generate ? undefined : 'Not a pilot topic, and expansion is not approved'}
              >
                <input
                  type="checkbox"
                  className="accent-brand-600"
                  disabled={!may_generate}
                  checked={topics.includes(topic.id)}
                  onChange={() => setTopics(toggle(topics, topic.id))}
                />
                {topic.name}
              </label>
            ))}
          </div>
          {eligible.length > 1 && (
            <button type="button" className="mt-2 text-xs font-semibold text-brand-700 hover:underline" onClick={() => setTopics(eligible.map((t) => t.topic.id))}>
              Select all eligible
            </button>
          )}
        </fieldset>
        <fieldset>
          <legend className="text-sm font-semibold text-slate-900">Components</legend>
          <div className="mt-2 flex flex-wrap gap-2">
            {SECTION_ORDER.map((component) => (
              <label
                key={component}
                className={cn(
                  'inline-flex cursor-pointer items-center gap-2 rounded-xl px-3 py-1.5 text-sm ring-1 ring-slate-200 ring-inset hover:bg-slate-50',
                  components.includes(component) && 'bg-brand-50 ring-brand-300',
                )}
              >
                <input type="checkbox" className="accent-brand-600" checked={components.includes(component)} onChange={() => setComponents(toggle(components, component))} />
                {SECTIONS[component].admin}
              </label>
            ))}
          </div>
          <p className="mt-2 text-xs text-slate-500">The playground is skipped for topics without an interactive widget.</p>
        </fieldset>
        <div className="grid gap-4 sm:grid-cols-2">
          <label className="flex items-start gap-3 text-sm">
            <input type="checkbox" className="mt-1 accent-brand-600" checked={useIntelligence} onChange={(e) => setUseIntelligence(e.target.checked)} />
            <span>
              <span className="font-medium text-slate-900">Use approved intelligence</span>
              <span className="block text-slate-500">Grounds interview questions in approved records and research. Companies never reach the model.</span>
            </span>
          </label>
          <TextField
            label="Spending limit per topic (USD)"
            type="number"
            min="0.1"
            max="100"
            step="0.1"
            value={limit}
            onChange={(e) => setLimit(e.target.value)}
            error={limitOk ? undefined : 'Between 0.1 and 100'}
          />
        </div>
        {skipped.length > 0 && (
          <Alert tone="info">
            Skipped: {skipped.map((s) => `${s.name ?? 'Unknown topic'} (${s.reason})`).join('; ')}
          </Alert>
        )}
        <div className="flex flex-wrap items-center gap-3">
          <Button icon={<Wand2 className="size-4" />} onClick={submit} disabled={!ready} loading={generate.isPending}>
            Generate drafts
          </Button>
          {!overview.ai_configured && <span className="text-sm text-slate-500">Needs the AI provider key.</span>}
          {overview.ai_configured && topics.length === 0 && (
            <span className="inline-flex items-center gap-1 text-sm text-slate-500">
              <Sparkles className="size-4" aria-hidden /> Pick at least one topic.
            </span>
          )}
        </div>
      </div>
    </Card>
  )
}
