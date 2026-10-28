import { ArrowRight, ChevronRight, Clock, SearchX } from 'lucide-react'
import { Link, useParams, useSearchParams } from 'react-router'

import { Button, ButtonLink } from '../../components/ui/Button'
import { TabScroller } from '../../components/ui/TabScroller'
import { Alert, Card, EmptyState, Skeleton } from '../../components/ui/Feedback'
import { SECTION_ORDER, SECTIONS, SectionBody, type ComponentKey } from '../../learn/sections'
import { ApiError, errorMessage } from '../../lib/api'
import { cn } from '../../lib/cn'
import { studentMediaUrl, useLearnTopic } from '../api'

export default function TopicPage() {
  const slug = useParams()['*'] ?? ''
  const topic = useLearnTopic(slug)
  const [params, setParams] = useSearchParams()

  const available = topic.data ? SECTION_ORDER.filter((key) => topic.data[key] !== null) : []
  const requested = SECTION_ORDER.find((key) => SECTIONS[key].slug === params.get('s'))
  const active: ComponentKey = requested && available.includes(requested) ? requested : 'lesson'
  const next = available[available.indexOf(active) + 1]

  const open = (key: ComponentKey) => {
    setParams(key === 'lesson' ? {} : { s: SECTIONS[key].slug })
    window.scrollTo({ top: 0, behavior: 'smooth' })
  }

  if (topic.isPending) {
    return (
      <div className="space-y-4">
        <Skeleton className="h-8 w-64" />
        <Skeleton className="h-5 w-96 max-w-full" />
        <Skeleton className="h-96 rounded-3xl" />
      </div>
    )
  }

  if (topic.isError) {
    if (topic.error instanceof ApiError && topic.error.status === 404) {
      return (
        <Card>
          <EmptyState
            icon={<SearchX className="size-6" />}
            title="This topic isn't available"
            action={<ButtonLink to="/app/learn">Back to Explore</ButtonLink>}
          >
            It may have moved or isn't published yet.
          </EmptyState>
        </Card>
      )
    }
    return (
      <Alert>
        {errorMessage(topic.error)}{' '}
        <Button size="sm" variant="ghost" onClick={() => topic.refetch()}>
          Retry
        </Button>
      </Alert>
    )
  }

  const data = topic.data
  const nextButton = next && (
    <div className="flex justify-end">
      <Button variant="glow" size="lg" onClick={() => open(next)}>
        Next: {SECTIONS[next].label} <ArrowRight className="size-4" />
      </Button>
    </div>
  )

  return (
    <div className="space-y-6">
      <header className="animate-fade-up">
        <nav aria-label="Breadcrumb" className="flex items-center gap-1 text-sm text-slate-500">
          <Link to="/app/learn" className="hover:text-slate-900">
            Explore
          </Link>
          <ChevronRight className="size-4" aria-hidden />
          <span>{data.domain.name}</span>
        </nav>
        <h1 className="mt-2 font-display text-3xl font-bold tracking-tight text-slate-900 sm:text-4xl">{data.name}</h1>
        <p className="mt-2 max-w-2xl text-lg text-slate-600">{data.tagline}</p>
        <div className="mt-3 flex flex-wrap gap-2 text-xs font-semibold">
          <span className="rounded-full bg-brand-50 px-2.5 py-1 text-brand-700 capitalize ring-1 ring-brand-100">{data.level}</span>
          <span className="inline-flex items-center gap-1 rounded-full bg-slate-100 px-2.5 py-1 text-slate-600">
            <Clock className="size-3.5" aria-hidden /> {data.minutes} min read
          </span>
        </div>
      </header>

      <div className="sticky top-16 z-20 -mx-4 border-b border-slate-200/70 bg-slate-50/85 px-4 py-2 backdrop-blur-xl sm:mx-0 sm:rounded-2xl sm:border sm:px-2">
        <TabScroller label="Sections" activeKey={active} fade="from-slate-50">
          {available.map((key) => {
            const meta = SECTIONS[key]
            const Icon = meta.icon
            const selected = key === active
            return (
              <button
                key={key}
                type="button"
                role="tab"
                aria-selected={selected}
                onClick={() => open(key)}
                className={cn(
                  'inline-flex shrink-0 items-center gap-1.5 rounded-xl px-3.5 py-2 text-sm font-semibold transition',
                  selected ? 'bg-slate-900 text-white shadow-sm' : 'text-slate-600 hover:bg-white hover:text-slate-900',
                )}
              >
                <Icon className="size-4" aria-hidden />
                {meta.label}
              </button>
            )
          })}
        </TabScroller>
      </div>

      <div key={active} role="tabpanel" aria-label={SECTIONS[active].label} className="animate-fade-up space-y-6">
        {active === 'video' && data.video && <h2 className="text-center font-display text-2xl font-bold text-slate-900">{data.video.title}</h2>}
        <SectionBody component={active} body={data[active]} audioUrl={studentMediaUrl} after={active === 'lesson' ? nextButton : undefined} />
        {active !== 'lesson' && nextButton}
      </div>
    </div>
  )
}
