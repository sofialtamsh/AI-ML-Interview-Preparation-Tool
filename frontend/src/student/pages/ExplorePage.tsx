import { ArrowRight, Clock, Compass, RefreshCw } from 'lucide-react'
import { Link } from 'react-router'

import { Button } from '../../components/ui/Button'
import { Alert, Card, EmptyState, PageHeader, Skeleton } from '../../components/ui/Feedback'
import { SECTIONS, type ComponentKey } from '../../learn/sections'
import { errorMessage } from '../../lib/api'
import type { LearnTopicCard } from '../../lib/types'
import { useLearnDomains } from '../api'

const DOMAIN_STYLE: Record<string, { gradient: string; emoji: string }> = {
  'machine-learning': { gradient: 'from-sky-500 via-brand-600 to-violet-600', emoji: '🤖' },
  'deep-learning': { gradient: 'from-fuchsia-500 via-brand-600 to-indigo-600', emoji: '🧠' },
}
const FALLBACK_STYLE = { gradient: 'from-brand-500 to-fuchsia-600', emoji: '✨' }

export function TopicCard({ topic, domainSlug }: { topic: LearnTopicCard; domainSlug: string }) {
  const style = DOMAIN_STYLE[domainSlug] ?? FALLBACK_STYLE
  return (
    <Link
      to={`/app/learn/${topic.slug}`}
      className="group flex flex-col overflow-hidden rounded-3xl bg-white shadow-sm ring-1 ring-slate-200 transition hover:-translate-y-0.5 hover:shadow-lg hover:ring-brand-300"
    >
      <div className={`flex items-center justify-between bg-gradient-to-br px-5 py-4 text-white ${style.gradient}`}>
        <span className="text-3xl" aria-hidden>
          {style.emoji}
        </span>
        <span className="flex items-center gap-1 rounded-full bg-white/20 px-2.5 py-0.5 text-xs font-semibold backdrop-blur">
          <Clock className="size-3.5" aria-hidden /> {topic.minutes} min
        </span>
      </div>
      <div className="flex flex-1 flex-col gap-2 p-5">
        <h3 className="font-display text-xl font-bold text-slate-900">{topic.name}</h3>
        <p className="flex-1 text-sm text-slate-600">{topic.tagline}</p>
        <div className="flex flex-wrap gap-1.5 pt-1" aria-label="Sections">
          {topic.sections.map((section) => {
            const meta = SECTIONS[section as ComponentKey]
            if (!meta) return null
            const Icon = meta.icon
            return (
              <span key={section} className="inline-flex items-center gap-1 rounded-full bg-slate-100 px-2 py-0.5 text-xs font-medium text-slate-600">
                <Icon className="size-3.5" aria-hidden />
                {meta.label}
              </span>
            )
          })}
        </div>
        <span className="mt-2 inline-flex items-center gap-1 text-sm font-semibold text-brand-700">
          <span className="capitalize">{topic.level}</span> · Start
          <ArrowRight className="size-4 transition group-hover:translate-x-1" aria-hidden />
        </span>
      </div>
    </Link>
  )
}

export default function ExplorePage() {
  const domains = useLearnDomains()

  return (
    <div className="space-y-8">
      <PageHeader title="Explore" description="Pick a topic. Swipe through the ideas, play with them, then prove it in a quiz." />

      {domains.isPending && (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {[0, 1, 2].map((i) => (
            <Skeleton key={i} className="h-64 rounded-3xl" />
          ))}
        </div>
      )}

      {domains.isError && (
        <Alert>
          {errorMessage(domains.error)}{' '}
          <Button size="sm" variant="ghost" icon={<RefreshCw className="size-4" />} onClick={() => domains.refetch()}>
            Retry
          </Button>
        </Alert>
      )}

      {domains.data?.length === 0 && (
        <Card>
          <EmptyState icon={<Compass className="size-6" />} title="Fresh topics are being prepared">
            The first AI/ML topics are still being reviewed. Check back soon.
          </EmptyState>
        </Card>
      )}

      {domains.data?.map((domain) => (
        <section key={domain.slug} aria-labelledby={`domain-${domain.slug}`} className="space-y-4">
          <h2 id={`domain-${domain.slug}`} className="font-display text-xl font-bold text-slate-900">
            {domain.name}
          </h2>
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {domain.topics.map((topic) => (
              <TopicCard key={topic.slug} topic={topic} domainSlug={domain.slug} />
            ))}
          </div>
        </section>
      ))}
    </div>
  )
}
