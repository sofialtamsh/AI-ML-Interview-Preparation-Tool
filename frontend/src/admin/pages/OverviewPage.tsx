import { ArrowRight, ShieldCheck, UserPlus } from 'lucide-react'
import { Link } from 'react-router'

import { DailyBarChart } from '../../components/charts/DailyBarChart'
import { Alert, Badge, Card, CardHeader, EmptyState, PageHeader, Skeleton } from '../../components/ui/Feedback'
import { errorMessage } from '../../lib/api'
import { cn } from '../../lib/cn'
import { formatCount, initials, timeAgo } from '../../lib/format'
import type { StudentStats } from '../../lib/types'
import { useCurrentAdmin, useOverview } from '../api'
import { StatusBadge } from '../StatusBadge'

function StatTile({ label, value, note }: { label: string; value: number; note?: string }) {
  return (
    <Card className="p-5">
      <p className="text-sm font-medium text-slate-500">{label}</p>
      <p className="mt-2 font-sans text-3xl font-semibold tracking-tight text-slate-900">
        {formatCount(value)}
      </p>
      {note && <p className="mt-1 text-xs text-slate-500">{note}</p>}
    </Card>
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
          value={stats.total}
          note={inactive ? `${inactive} suspended or deactivated` : 'All accounts active'}
        />
        <StatTile
          label="Active in the last 7 days"
          value={stats.active_last_7_days}
          note="Used the platform at least once"
        />
        <StatTile label="New this week" value={stats.new_last_7_days} note="Last 7 days" />
        <StatTile label="New this month" value={stats.new_last_30_days} note="Last 30 days" />
        {activeAdmins !== null && (
          <StatTile label="Active admins" value={activeAdmins} note="Can sign in to this console" />
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
                <StatTile label="Active admins" value={overview.data.active_admins} />
              </div>
            )
          )}
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
