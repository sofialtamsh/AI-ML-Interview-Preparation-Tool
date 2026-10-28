import { ChevronRight, Wand2 } from 'lucide-react'
import { useState } from 'react'
import { Link, useParams, useSearchParams } from 'react-router'

import { Button } from '../../../components/ui/Button'
import { TabScroller } from '../../../components/ui/TabScroller'
import { Dialog } from '../../../components/ui/Dialog'
import { Alert, Badge, Card, CardHeader, EmptyState, Skeleton } from '../../../components/ui/Feedback'
import { useToast } from '../../../components/ui/Toast'
import { SECTION_ORDER, SECTIONS } from '../../../learn/sections'
import { errorMessage } from '../../../lib/api'
import { cn } from '../../../lib/cn'
import { timeAgo } from '../../../lib/format'
import type { ContentComponent, TopicContent } from '../../../lib/types'
import { useCan } from '../../api'
import { useBulkTransition, useContentOverview, useGenerate, useTopicContent } from '../../contentApi'
import { ContentRuns, ORIGIN_LABELS, VERSION_STATUS, VersionStatusBadge } from './shared'
import { VersionPanel } from './VersionPanel'

export default function TopicContentPage() {
  const { topicId = '' } = useParams()
  const state = useTopicContent(topicId)
  const overview = useContentOverview()
  const [params, setParams] = useSearchParams()

  const requested = params.get('c') as ContentComponent | null
  const component: ContentComponent = requested && SECTION_ORDER.includes(requested) ? requested : 'lesson'
  const current = state.data?.components.find((c) => c.component === component)
  const versionId = params.get('v') && current?.versions.some((v) => v.id === params.get('v')) ? params.get('v')! : (current?.latest?.id ?? null)

  const select = (next: { c?: ContentComponent; v?: string }) => {
    const c = next.c ?? component
    setParams(next.v ? { c, v: next.v } : { c })
  }

  if (state.isPending) return <Skeleton className="h-96 rounded-2xl" />
  if (state.isError) return <Alert>{errorMessage(state.error)}</Alert>
  const data = state.data

  return (
    <div className="space-y-6">
      <header>
        <nav aria-label="Breadcrumb" className="flex items-center gap-1 text-sm text-slate-500">
          <Link to="/admin/content" className="hover:text-slate-900">
            Content studio
          </Link>
          <ChevronRight className="size-4" aria-hidden />
          <span>{data.topic.domain_name}</span>
        </nav>
        <div className="mt-2 flex flex-wrap items-end justify-between gap-4">
          <div>
            <h1 className="flex flex-wrap items-center gap-2 font-display text-2xl font-bold tracking-tight text-slate-900 sm:text-3xl">
              {data.topic.name}
              {data.topic.is_pilot && <Badge tone="brand">Pilot</Badge>}
            </h1>
            <p className="mt-1 font-mono text-xs text-slate-500">{data.topic.slug}</p>
          </div>
          <TopicActions topic={data} aiConfigured={!!overview.data?.ai_configured} />
        </div>
      </header>

      <div className="rounded-2xl bg-white p-1.5 ring-1 ring-slate-200">
        <TabScroller label="Components" activeKey={component}>
        {data.components.map((c) => {
          const Icon = SECTIONS[c.component].icon
          const status = c.latest?.status
          return (
            <button
              key={c.component}
              type="button"
              role="tab"
              aria-selected={c.component === component}
              onClick={() => select({ c: c.component })}
              className={cn(
                'inline-flex shrink-0 items-center gap-2 rounded-xl px-3 py-2 text-sm font-medium transition',
                c.component === component ? 'bg-slate-900 text-white' : 'text-slate-600 hover:bg-slate-100',
              )}
            >
              <Icon className="size-4" aria-hidden />
              {SECTIONS[c.component].admin}
              <span
                className={cn('size-2 rounded-full', status ? VERSION_STATUS[status].dot : 'bg-slate-200', c.published_number !== null && 'ring-2 ring-emerald-400')}
                aria-label={`${status ? VERSION_STATUS[status].label : 'No content'}${c.published_number ? ', live' : ''}`}
              />
            </button>
          )
        })}
        </TabScroller>
      </div>

      {!current || current.versions.length === 0 || !versionId ? (
        <Card>
          <EmptyState icon={<Wand2 className="size-6" />} title={`No ${SECTIONS[component].admin.toLowerCase()} yet`}>
            {component === 'playground' && !data.has_playground
              ? 'This topic has no interactive playground widget yet, so this component stays empty.'
              : 'Generate a draft for this topic, then review it here.'}
          </EmptyState>
        </Card>
      ) : (
        <div className="grid items-start gap-4 lg:grid-cols-[15rem_minmax(0,1fr)]">
          <Card className="overflow-hidden">
            <CardHeader title="Versions" description={current.published_number ? `v${current.published_number} is live` : 'Nothing live yet'} />
            <ol className="max-h-[32rem] divide-y divide-slate-100 overflow-y-auto">
              {current.versions.map((v) => (
                <li key={v.id}>
                  <button
                    type="button"
                    onClick={() => select({ v: v.id })}
                    aria-current={v.id === versionId}
                    className={cn('w-full px-4 py-3 text-left transition hover:bg-slate-50', v.id === versionId && 'bg-brand-50/60')}
                  >
                    <span className="flex items-center justify-between gap-2">
                      <span className="font-semibold text-slate-900">v{v.number}</span>
                      <VersionStatusBadge status={v.status} />
                    </span>
                    <span className="mt-0.5 block text-xs text-slate-500">
                      {ORIGIN_LABELS[v.origin]} · {timeAgo(v.created_at)}
                    </span>
                  </button>
                </li>
              ))}
            </ol>
          </Card>
          <VersionPanel
            key={versionId}
            topicId={topicId}
            component={component}
            versionId={versionId}
            versions={current.versions}
            overview={overview.data}
            onSelect={(id) => select({ v: id })}
          />
        </div>
      )}

      <Card className="overflow-hidden">
        <CardHeader title="Runs for this topic" description="Generation and narration jobs, with their log and cost." />
        <ContentRuns topicId={topicId} pageSize={5} />
      </Card>
    </div>
  )
}

function TopicActions({ topic, aiConfigured }: { topic: TopicContent; aiConfigured: boolean }) {
  const bulk = useBulkTransition(topic.topic.id)
  const toast = useToast()
  const canSubmit = useCan('content.generate', 'content.review')
  const canPublish = useCan('content.publish')
  const canGenerate = useCan('content.generate')
  const [generating, setGenerating] = useState(false)

  const statuses = topic.components.map((c) => c.latest?.status)
  const has = (status: string) => statuses.includes(status as never)

  const runBulk = (action: 'submit' | 'approve' | 'publish') =>
    bulk.mutate(action, {
      onSuccess: (result) => {
        const skipped = Object.entries(result.skipped)
        if (result.changed.length) toast.success(`Done for: ${result.changed.join(', ')}`)
        if (skipped.length) toast.error(`Skipped ${skipped.map(([c, reason]) => `${c} (${reason})`).join('; ')}`)
        if (!result.changed.length && !skipped.length) toast.success('Nothing to change')
      },
      onError: (error) => toast.error(errorMessage(error)),
    })

  return (
    <div className="flex flex-wrap gap-2">
      {canSubmit && has('draft') && (
        <Button size="sm" variant="secondary" loading={bulk.isPending && bulk.variables === 'submit'} onClick={() => runBulk('submit')}>
          Submit all drafts
        </Button>
      )}
      {canPublish && has('under_review') && (
        <Button size="sm" variant="secondary" loading={bulk.isPending && bulk.variables === 'approve'} onClick={() => runBulk('approve')}>
          Approve all in review
        </Button>
      )}
      {canPublish && has('approved') && (
        <Button size="sm" loading={bulk.isPending && bulk.variables === 'publish'} onClick={() => runBulk('publish')}>
          Publish all approved
        </Button>
      )}
      {canGenerate && aiConfigured && topic.may_generate && (
        <Button size="sm" variant="secondary" icon={<Wand2 className="size-4" />} onClick={() => setGenerating(true)}>
          Generate…
        </Button>
      )}
      {generating && <GenerateDialog topic={topic} onClose={() => setGenerating(false)} />}
    </div>
  )
}

function GenerateDialog({ topic, onClose }: { topic: TopicContent; onClose: () => void }) {
  const generate = useGenerate()
  const toast = useToast()
  const options = SECTION_ORDER.filter((c) => c !== 'playground' || topic.has_playground)
  const [components, setComponents] = useState<ContentComponent[]>(options)

  return (
    <Dialog
      open
      onClose={onClose}
      title={`Generate drafts for ${topic.topic.name}`}
      description="Each component arrives as a new draft version for review."
      footer={
        <>
          <Button variant="secondary" onClick={onClose}>
            Cancel
          </Button>
          <Button
            icon={<Wand2 className="size-4" />}
            disabled={components.length === 0}
            loading={generate.isPending}
            onClick={() =>
              generate.mutate(
                { topic_ids: [topic.topic.id], components, use_intelligence: true, max_cost_usd: '2' },
                {
                  onSuccess: (result) => {
                    if (result.started.length) toast.success('Generation started. Follow it under Runs.')
                    else toast.error(result.skipped[0]?.reason ?? 'Nothing started')
                    onClose()
                  },
                  onError: (error) => toast.error(errorMessage(error)),
                },
              )
            }
          >
            Generate
          </Button>
        </>
      }
    >
      <fieldset className="flex flex-wrap gap-2">
        <legend className="sr-only">Components</legend>
        {options.map((c) => (
          <label key={c} className={cn('inline-flex cursor-pointer items-center gap-2 rounded-xl px-3 py-1.5 text-sm ring-1 ring-slate-200 ring-inset', components.includes(c) && 'bg-brand-50 ring-brand-300')}>
            <input
              type="checkbox"
              className="accent-brand-600"
              checked={components.includes(c)}
              onChange={() => setComponents(components.includes(c) ? components.filter((x) => x !== c) : [...components, c])}
            />
            {SECTIONS[c].admin}
          </label>
        ))}
      </fieldset>
      <p className="mt-3 text-xs text-slate-500">Uses approved interview intelligence; spending limit $2 for this run.</p>
    </Dialog>
  )
}
