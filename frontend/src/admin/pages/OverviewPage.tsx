import { ArrowRight, ShieldCheck, UserPlus } from 'lucide-react'
import { Link } from 'react-router'

import { DailyBarChart } from '../../components/charts/DailyBarChart'
import { Alert, Badge, Card, CardHeader, EmptyState, PageHeader, Skeleton } from '../../components/ui/Feedback'
import { StatTile } from '../../components/ui/StatTile'
import { ProgressBar } from '../../learn/progress'
import { errorMessage } from '../../lib/api'
import { cn } from '../../lib/cn'
import { formatCount, formatDuration, initials, timeAgo } from '../../lib/format'
import type { StudentStats } from '../../lib/types'
import { defaultAnalyticsFilters, useAnalytics, useCan, useCurrentAdmin, useOverview } from '../api'
import { StatusBadge } from '../StatusBadge'

const pct = (value: number | null) => (value === null ? '—' : `${Math.round(value)}%`)

/** The learning side of the platform over the last 30 days (needs analytics.view). */
function LearningSection() {
  const analytics = useAnalytics(defaultAnalyticsFilters())
  const report = analytics.data
  const topics = report ? [...report.topics].sort((a, b) => b.started - a.started).slice(0, 6) : []

  return (
    <section aria-labelledby="learning-heading" className="space-y-4">
      <div className="flex flex-wrap items-end justify-between gap-2">
        <div>
          <h2 id="learning-heading" className="text-lg font-semibold text-slate-900">
            Learning
          </h2>
          <p className="text-sm text-slate-500">Last 30 days, every student.</p>
        </div>
        <Link to="/admin/analytics" className="inline-flex items-center gap-1 text-sm font-semibold text-brand-700 hover:text-brand-800">
          Open analytics <ArrowRight className="size-4" aria-hidden />
        </Link>
      </div>

      {analytics.isPending ? (
        <Skeleton className="h-40 rounded-2xl" />
      ) : analytics.isError ? (
        <Alert>{errorMessage(analytics.error)}</Alert>
      ) : (
        report && (
          <>
            <div className="grid grid-cols-2 gap-3 lg:grid-cols-3 xl:grid-cols-6">
              <StatTile
                label="Active learners"
                value={formatCount(report.kpis.active_students)}
                note={report.kpis.students ? `${Math.round((report.kpis.active_students * 100) / report.kpis.students)}% of students` : 'No students yet'}
              />
              <StatTile label="Average path completion" value={pct(report.kpis.average_completion)} note="Live sections done" />
              <StatTile
                label="Learning time"
                value={formatDuration(report.kpis.learning_seconds)}
                note={report.kpis.learning_seconds_per_learner !== null ? `${formatDuration(report.kpis.learning_seconds_per_learner)} per learner` : 'None yet'}
              />
              <StatTile label="Quiz average" value={pct(report.kpis.quiz_average)} note={`${formatCount(report.kpis.quiz_attempts)} attempt(s)`} />
              <StatTile
                label="Interview practice"
                value={report.kpis.practice_average !== null ? `${report.kpis.practice_average.toFixed(1)}/10` : '—'}
                note={`${formatCount(report.kpis.practice_answers)} answer(s) scored`}
              />
              <StatTile
                label="Need attention"
                value={formatCount(report.kpis.needing_attention)}
                note={
                  <Link to="/admin/students?attention=any" className="inline-flex items-center gap-1 font-semibold text-brand-700 hover:underline">
                    See who <ArrowRight className="size-3" aria-hidden />
                  </Link>
                }
              />
            </div>

            <div className="grid gap-6 xl:grid-cols-2">
              <Card>
                <CardHeader title="Completion by domain" description="Students who finished a topic, out of those who started it." />
                <ul className="space-y-4 px-5 pb-5">
                  {report.domains.map((d) => (
                    <li key={d.name}>
                      <div className="flex justify-between gap-3 text-sm">
                        <span className="font-medium text-slate-900">{d.name}</span>
                        <span className="text-slate-600 tabular-nums">
                          {d.completion_rate === null ? 'Not started' : `${d.completion_rate}% complete`} · quiz {pct(d.quiz_average)}
                        </span>
                      </div>
                      <ProgressBar value={d.completion_rate ?? 0} label={`${d.name} completion rate`} className="mt-1.5" />
                    </li>
                  ))}
                  {report.domains.length === 0 && <li className="text-sm text-slate-600">No topics are live yet.</li>}
                </ul>
              </Card>
              <Card>
                <CardHeader title="Topic completion" description="The most-started topics: how many finished, and the quiz average." />
                <ul className="divide-y divide-slate-100">
                  {topics.map((t) => (
                    <li key={t.slug} className="flex items-center gap-3 px-5 py-2.5 text-sm">
                      <span className="min-w-0 flex-1">
                        <span className="block truncate font-medium text-slate-900">{t.name}</span>
                        <span className="block text-xs text-slate-500">
                          {t.completed}/{t.started} finished · quiz {pct(t.quiz_average)}
                        </span>
                      </span>
                      <ProgressBar value={t.completion_rate ?? 0} label={`${t.name} completion rate`} className="w-24 sm:w-32" />
                      <span className="w-9 text-right text-xs text-slate-600 tabular-nums">{t.completion_rate === null ? '—' : `${t.completion_rate}%`}</span>
                    </li>
                  ))}
                  {topics.length === 0 && <li className="px-5 pb-5 text-sm text-slate-600">No topics are live yet.</li>}
                </ul>
              </Card>
            </div>
          </>
        )
      )}
    </section>
  )
}

function StudentSection({
  stats,
  activeAdmins,
}: {
  stats: StudentStats
  activeAdmins: number | null
}) {
  const inactive = (stats.by_status.suspended ?? 0) + (stats.by_status.deactivated ?? 0)
  return (
    <>
      <div
        className={cn(
          'grid grid-cols-1 gap-4 sm:grid-cols-2',
          activeAdmins === null ? 'xl:grid-cols-4' : 'lg:grid-cols-3 xl:grid-cols-5',
        )}
      >
        <StatTile
          label="Registered students"
          value={formatCount(stats.total)}
          note={inactive ? `${inactive} suspended or deactivated` : 'All accounts active'}
        />
        <StatTile
          label="Active in the last 7 days"
          value={formatCount(stats.active_last_7_days)}
          note="Used the platform at least once"
        />
        <StatTile label="New this week" value={formatCount(stats.new_last_7_days)} note="Last 7 days" />
        <StatTile label="New this month" value={formatCount(stats.new_last_30_days)} note="Last 30 days" />
        {activeAdmins !== null && (
          <StatTile label="Active admins" value={formatCount(activeAdmins)} note="Can sign in to this console" />
        )}
      </div>

      <div className="grid grid-cols-1 gap-6 xl:grid-cols-3">
        <Card className="xl:col-span-2">
          <CardHeader title="Daily registrations" description="Last 30 days (UTC)" />
          <div className="p-5">
            <DailyBarChart
              data={stats.registrations_last_30_days}
              label="Daily student registrations over the last 30 days"
            />
          </div>
        </Card>

        <Card>
          <CardHeader
            title="Latest registrations"
            action={
              <Link
                to="/admin/students"
                className="inline-flex items-center gap-1 text-sm font-semibold text-brand-700 hover:text-brand-800"
              >
                All <ArrowRight className="size-4" aria-hidden />
              </Link>
            }
          />
          {stats.recent.length === 0 ? (
            <EmptyState icon={<UserPlus className="size-6" />} title="No students yet">
              New registrations will appear here.
            </EmptyState>
          ) : (
            <ul className="divide-y divide-slate-100">
              {stats.recent.map((s) => (
                <li key={s.id}>
                  <Link
                    to={`/admin/students/${s.id}`}
                    className="flex items-center gap-3 px-5 py-3 transition hover:bg-slate-50"
                  >
                    <span className="grid size-9 shrink-0 place-items-center rounded-full bg-brand-50 text-xs font-bold text-brand-700">
                      {initials(s.full_name)}
                    </span>
                    <span className="min-w-0 flex-1">
                      <span className="block truncate text-sm font-medium text-slate-900">
                        {s.full_name}
                      </span>
                      <span className="block truncate text-xs text-slate-500">
                        {s.student_code} · joined {timeAgo(s.created_at).toLowerCase()}
                      </span>
                    </span>
                    <StatusBadge status={s.status} />
                  </Link>
                </li>
              ))}
            </ul>
          )}
        </Card>
      </div>
    </>
  )
}

export default function OverviewPage() {
  const admin = useCurrentAdmin()
  const overview = useOverview()
  const canSeeLearning = useCan('analytics.view')

  return (
    <div className="space-y-6">
      <PageHeader
        title="Overview"
        description={`Welcome back, ${admin.full_name.split(' ')[0]}. Here's the current state of the platform.`}
      />

      {overview.isPending ? (
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-4">
          {[0, 1, 2, 3].map((i) => (
            <Skeleton key={i} className="h-28 rounded-2xl" />
          ))}
        </div>
      ) : overview.isError ? (
        <Alert>{errorMessage(overview.error)}</Alert>
      ) : (
        <>
          {overview.data.students ? (
            <StudentSection
              stats={overview.data.students}
              activeAdmins={overview.data.active_admins}
            />
          ) : (
            overview.data.active_admins !== null && (
              <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-4">
                <StatTile label="Active admins" value={formatCount(overview.data.active_admins)} />
              </div>
            )
          )}
          {canSeeLearning && <LearningSection />}
          {!overview.data.students && (
            <Card>
              <CardHeader
                title="Your access"
                description="Sections appear in the sidebar according to your role."
              />
              <div className="flex flex-wrap items-center gap-2 p-5">
                <ShieldCheck className="size-5 text-brand-600" aria-hidden />
                {admin.roles.map((r) => (
                  <Badge key={r.id} tone="brand">
                    {r.name}
                  </Badge>
                ))}
              </div>
            </Card>
          )}
        </>
      )}
    </div>
  )
}
