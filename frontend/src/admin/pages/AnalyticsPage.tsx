import { ArrowRight, BarChart3, Download } from 'lucide-react'
import { useState } from 'react'
import { Link, useSearchParams } from 'react-router'

import { BarChart } from '../../components/charts/BarChart'
import { buttonClasses } from '../../components/ui/Button'
import { Alert, Card, CardHeader, EmptyState, PageHeader, Skeleton } from '../../components/ui/Feedback'
import { SelectField, TextField } from '../../components/ui/Field'
import { StatTile } from '../../components/ui/StatTile'
import { ProgressBar } from '../../learn/progress'
import { errorMessage } from '../../lib/api'
import { cn } from '../../lib/cn'
import { formatCount, formatDuration } from '../../lib/format'
import type { AnalyticsReport } from '../../lib/types'
import { analyticsParams, daysAgo, defaultAnalyticsFilters, today, useAnalytics, useCan, type AnalyticsFilters } from '../api'
import { StudentPicker, type PickedStudent } from '../StudentPicker'

const RANGES = [
  { days: 7, label: 'Last 7 days' },
  { days: 30, label: 'Last 30 days' },
  { days: 90, label: 'Last 90 days' },
  { days: 365, label: 'Last year' },
]

const shortDay = new Intl.DateTimeFormat(undefined, { day: 'numeric', month: 'short' })
const longDay = new Intl.DateTimeFormat(undefined, { weekday: 'short', day: 'numeric', month: 'short', year: 'numeric' })
const parseDay = (day: string) => new Date(`${day}T00:00:00`)
const pct = (value: number | null) => (value === null ? '—' : `${Math.round(value)}%`)

function Kpis({ report }: { report: AnalyticsReport }) {
  const k = report.kpis
  return (
    <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
      <StatTile label="Students" value={formatCount(k.students)} note={`${formatCount(k.new_students)} new in this range`} />
      <StatTile label="Active learners" value={formatCount(k.active_students)} note={k.students ? `${Math.round((k.active_students * 100) / k.students)}% of students` : 'No students yet'} />
      <StatTile label="Average path completion" value={pct(k.average_completion)} note="Live sections done, averaged over students" />
      <StatTile
        label="Learning time"
        value={formatDuration(k.learning_seconds)}
        note={k.learning_seconds_per_learner !== null ? `${formatDuration(k.learning_seconds_per_learner)} per learner` : 'None in this range'}
      />
      <StatTile label="Quiz attempts" value={formatCount(k.quiz_attempts)} note={`Average ${pct(k.quiz_average)}`} />
      <StatTile label="Practice answers scored" value={formatCount(k.practice_answers)} note={k.practice_average !== null ? `Average ${k.practice_average.toFixed(1)}/10` : 'None yet'} />
      <StatTile label="Live topics" value={formatCount(k.published_topics)} note={`${k.published_sections} sections`} />
      <StatTile
        label="Need attention"
        value={formatCount(k.needing_attention)}
        note={
          <Link to="/admin/students?attention=any" className="inline-flex items-center gap-1 font-semibold text-brand-700 hover:underline">
            See who <ArrowRight className="size-3" aria-hidden />
          </Link>
        }
      />
    </div>
  )
}

function TopicTable({ report }: { report: AnalyticsReport }) {
  return (
    <Card className="overflow-hidden">
      <CardHeader title="Topic completion and performance" description="Completion rate is students who finished every section, out of those who started the topic." />
      {report.topics.length === 0 ? (
        <EmptyState icon={<BarChart3 className="size-6" />} title="No live topics in this filter" />
      ) : (
        <div className="overflow-x-auto">
          <table className="w-full min-w-[50rem] text-left text-sm">
            <thead className="bg-slate-50 text-xs text-slate-500">
              <tr>
                {['Topic', 'Started', 'Completed', 'Completion rate', 'Quiz average', 'Practice average', 'Learning time'].map((h) => (
                  <th key={h} scope="col" className="px-4 py-2 font-medium first:pl-5">
                    {h}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {report.topics.map((topic) => (
                <tr key={topic.slug}>
                  <td className="px-4 py-2.5 pl-5">
                    <span className="font-medium text-slate-900">{topic.name}</span>
                    <span className="block text-xs text-slate-500">{topic.domain}</span>
                  </td>
                  <td className="px-4 py-2.5 tabular-nums">{topic.started}</td>
                  <td className="px-4 py-2.5 tabular-nums">{topic.completed}</td>
                  <td className="w-44 px-4 py-2.5">
                    {topic.completion_rate === null ? (
                      <span className="text-slate-400">—</span>
                    ) : (
                      <div className="flex items-center gap-2">
                        <ProgressBar value={topic.completion_rate} label={`${topic.name} completion rate`} className="flex-1" />
                        <span className="w-9 text-right text-xs text-slate-600 tabular-nums">{topic.completion_rate}%</span>
                      </div>
                    )}
                  </td>
                  <td className="px-4 py-2.5 tabular-nums">
                    {pct(topic.quiz_average)} <span className="text-xs text-slate-400">({topic.quiz_attempts})</span>
                  </td>
                  <td className="px-4 py-2.5 tabular-nums">
                    {topic.practice_average !== null ? `${topic.practice_average.toFixed(1)}/10` : '—'}{' '}
                    <span className="text-xs text-slate-400">({topic.practice_answers})</span>
                  </td>
                  <td className="px-4 py-2.5 tabular-nums">{formatDuration(topic.learning_seconds)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </Card>
  )
}

export default function AnalyticsPage() {
  const [params, setParams] = useSearchParams()
  const canExport = useCan('analytics.export')
  const canSeeStudents = useCan('students.view')
  const defaults = defaultAnalyticsFilters()
  const filters: AnalyticsFilters = {
    start: params.get('start') ?? defaults.start,
    end: params.get('end') ?? defaults.end,
    cohort_id: params.get('cohort_id') ?? '',
    domain: params.get('domain') ?? '',
    topic: params.get('topic') ?? '',
    student_id: canSeeStudents ? (params.get('student_id') ?? '') : '',
  }
  const analytics = useAnalytics(filters)
  const report = analytics.data
  const set = (changes: Partial<AnalyticsFilters>) => setParams(analyticsParams({ ...filters, ...changes }), { replace: true })
  const preset = RANGES.find((r) => filters.start === daysAgo(r.days - 1) && filters.end === today())
  // The picked student shows straight away; after a reload their name comes from the report.
  const [picked, setPicked] = useState<PickedStudent | null>(null)
  const student = !filters.student_id
    ? null
    : report?.student?.id === filters.student_id
      ? report.student
      : picked?.id === filters.student_id
        ? picked
        : { id: filters.student_id, full_name: 'Selected student', student_code: '' }

  return (
    <div className="space-y-6">
      <PageHeader
        title="Analytics"
        description="How students are learning: activity, completion, quiz and interview-practice performance, weak topics and cohorts."
        actions={
          canExport && (
            <a href={`/api/admin/analytics/students.csv${filters.cohort_id ? `?cohort_id=${filters.cohort_id}` : ''}`} className={buttonClasses('secondary')} download>
              <Download className="size-4" aria-hidden /> Export students (CSV)
            </a>
          )
        }
      />

      <Card className="p-4">
        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
          <SelectField
            label="Range"
            value={preset ? String(preset.days) : 'custom'}
            onChange={(e) => {
              const days = Number(e.target.value)
              if (days) set({ start: daysAgo(days - 1), end: today() })
            }}
          >
            {RANGES.map((r) => (
              <option key={r.days} value={r.days}>
                {r.label}
              </option>
            ))}
            <option value="custom" disabled={!!preset}>
              Custom
            </option>
          </SelectField>
          <TextField label="From" type="date" value={filters.start} max={filters.end} onChange={(e) => e.target.value && set({ start: e.target.value })} />
          <TextField label="To" type="date" value={filters.end} min={filters.start} onChange={(e) => e.target.value && set({ end: e.target.value })} />
          <SelectField label="Cohort" value={filters.cohort_id} onChange={(e) => set({ cohort_id: e.target.value })}>
            <option value="">All cohorts</option>
            {report?.filters.cohorts.map((c) => (
              <option key={c.id} value={c.id}>
                {c.name}
              </option>
            ))}
          </SelectField>
          <SelectField label="Domain" value={filters.domain} onChange={(e) => set({ domain: e.target.value, topic: '' })}>
            <option value="">All domains</option>
            {report?.filters.domains.map((d) => (
              <option key={d.slug} value={d.slug}>
                {d.name}
              </option>
            ))}
          </SelectField>
          <SelectField label="Topic" value={filters.topic} onChange={(e) => set({ topic: e.target.value })}>
            <option value="">All topics</option>
            {report?.filters.topics.map((t) => (
              <option key={t.slug} value={t.slug}>
                {t.name}
              </option>
            ))}
          </SelectField>
          {canSeeStudents && (
            <StudentPicker
              selected={student}
              onChange={(next) => {
                setPicked(next)
                set({ student_id: next?.id ?? '' })
              }}
            />
          )}
        </div>
      </Card>

      {student && (
        <Alert tone="info">
          Showing only {student.full_name}&apos;s learning.{' '}
          <Link to={`/admin/students/${student.id}`} className="font-semibold text-brand-700 hover:underline">
            Open their profile
          </Link>
        </Alert>
      )}

      {analytics.isPending && <Skeleton className="h-96 rounded-2xl" />}
      {analytics.isError && <Alert>{errorMessage(analytics.error)}</Alert>}

      {report && (
        <div className={cn('space-y-6 transition-opacity', analytics.isPlaceholderData && 'opacity-60')}>
          <Kpis report={report} />

          <div className="grid gap-6 xl:grid-cols-2">
            <Card>
              <CardHeader title="Registrations" description="New student accounts per day." />
              <div className="p-5">
                <BarChart
                  data={report.registrations.map((r) => ({ key: r.day, label: shortDay.format(parseDay(r.day)), long: longDay.format(parseDay(r.day)), value: r.count }))}
                  label="Registrations per day"
                  unit={['registration', 'registrations']}
                  column="Day"
                />
              </div>
            </Card>
            <Card>
              <CardHeader title="Active learners per week" description="Students who studied, took a quiz or practised that week." />
              <div className="p-5">
                <BarChart
                  data={report.weekly_active.map((w) => ({
                    key: w.week,
                    label: shortDay.format(parseDay(w.week)),
                    long: `Week of ${longDay.format(parseDay(w.week))}`,
                    value: w.count,
                  }))}
                  label="Active learners per week"
                  unit={['learner', 'learners']}
                  column="Week"
                />
              </div>
            </Card>
          </div>

          <div className="grid gap-6 xl:grid-cols-3">
            <Card className="xl:col-span-2">
              <CardHeader title="Quiz score distribution" description="Every quiz attempt in this range, by score." />
              <div className="p-5">
                <BarChart
                  data={report.score_distribution.map((b) => ({ key: String(b.from), label: `${b.from}%`, long: `${b.from}–${b.to}%`, value: b.count }))}
                  label="Quiz attempts by score"
                  unit={['attempt', 'attempts']}
                  column="Score"
                />
              </div>
            </Card>
            <Card>
              <CardHeader title="Weak topics" description="Lowest quiz averages (topics with 3+ attempts)." />
              {report.weak_topics.length === 0 ? (
                <p className="px-5 pb-5 text-sm text-slate-600">Not enough quiz attempts yet to call out weak topics.</p>
              ) : (
                <ol className="divide-y divide-slate-100">
                  {report.weak_topics.map((t, i) => (
                    <li key={t.slug} className="flex items-center gap-3 px-5 py-2.5 text-sm">
                      <span className="w-5 text-xs font-bold text-slate-400">{i + 1}</span>
                      <span className="min-w-0 flex-1 font-medium text-slate-900">{t.name}</span>
                      <span className="font-semibold text-amber-800 tabular-nums">{pct(t.quiz_average)}</span>
                    </li>
                  ))}
                </ol>
              )}
            </Card>
          </div>

          <TopicTable report={report} />

          <div className="grid gap-6 xl:grid-cols-2">
            <Card>
              <CardHeader title="Domains" description="Completion rate and quiz average per domain." />
              <ul className="space-y-4 p-5">
                {report.domains.map((d) => (
                  <li key={d.name}>
                    <div className="flex justify-between text-sm">
                      <span className="font-medium text-slate-900">{d.name}</span>
                      <span className="text-slate-600 tabular-nums">
                        {d.completion_rate === null ? 'Not started' : `${d.completion_rate}% complete`} · quiz {pct(d.quiz_average)}
                      </span>
                    </div>
                    <ProgressBar value={d.completion_rate ?? 0} label={`${d.name} completion rate`} className="mt-1.5" />
                  </li>
                ))}
                {report.domains.length === 0 && <li className="text-sm text-slate-600">No live topics in this filter.</li>}
              </ul>
            </Card>
            <Card className="overflow-hidden">
              <CardHeader title="Cohorts" description="Students, how many were active in this range, and their quiz average." />
              {report.student ? (
                <p className="px-5 pb-5 text-sm text-slate-600">Cohorts aren&apos;t compared while one student is selected.</p>
              ) : report.cohorts.length === 0 ? (
                <p className="px-5 pb-5 text-sm text-slate-600">No cohorts yet. Create them on the Students page.</p>
              ) : (
                <table className="w-full text-left text-sm">
                  <thead className="bg-slate-50 text-xs text-slate-500">
                    <tr>
                      <th scope="col" className="px-5 py-2 font-medium">
                        Cohort
                      </th>
                      <th scope="col" className="px-3 py-2 font-medium">
                        Students
                      </th>
                      <th scope="col" className="px-3 py-2 font-medium">
                        Active
                      </th>
                      <th scope="col" className="px-5 py-2 font-medium">
                        Quiz average
                      </th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-100">
                    {report.cohorts.map((c) => (
                      <tr key={c.name}>
                        <td className="px-5 py-2.5 font-medium text-slate-900">{c.name}</td>
                        <td className="px-3 py-2.5 tabular-nums">{c.students}</td>
                        <td className="px-3 py-2.5 tabular-nums">{c.active}</td>
                        <td className="px-5 py-2.5 tabular-nums">{pct(c.quiz_average)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              )}
            </Card>
          </div>
        </div>
      )}
    </div>
  )
}
