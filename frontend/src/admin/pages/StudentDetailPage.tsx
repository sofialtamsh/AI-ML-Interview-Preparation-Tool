import { ArrowLeft, CircleCheck, CircleX, Lock } from 'lucide-react'
import { useState } from 'react'
import { Link, useParams } from 'react-router'

import { Button } from '../../components/ui/Button'
import { Dialog } from '../../components/ui/Dialog'
import { Alert, Badge, Card, CardHeader, EmptyState, Skeleton } from '../../components/ui/Feedback'
import { SelectField } from '../../components/ui/Field'
import { useToast } from '../../components/ui/Toast'
import { errorMessage } from '../../lib/api'
import { describeDevice, formatDate, formatDateTime, initials, timeAgo } from '../../lib/format'
import type { StudentDetail, StudentStatus } from '../../lib/types'
import { useCan, useCohorts, useStudent, useUpdateStudent } from '../api'
import { StatusBadge } from '../StatusBadge'

const FAILURE_LABELS: Record<string, string> = {
  bad_password: 'Wrong password',
  locked: 'Blocked: account locked',
  status_suspended: 'Blocked: account suspended',
  status_deactivated: 'Blocked: account deactivated',
}

const STATUS_HELP: Record<StudentStatus, string> = {
  active: 'The student can sign in and learn.',
  suspended: 'Temporarily blocks sign-in. The student is signed out on every device.',
  deactivated: 'Closes the account. The student is signed out on every device.',
}

function ManageCard({ student }: { student: StudentDetail }) {
  const update = useUpdateStudent(student.id)
  const cohorts = useCohorts()
  const toast = useToast()
  const [status, setStatus] = useState<StudentStatus>(student.status)
  const [cohortId, setCohortId] = useState(student.cohort?.id ?? '')
  const [confirming, setConfirming] = useState(false)

  const statusChanged = status !== student.status
  const cohortChanged = cohortId !== (student.cohort?.id ?? '')

  const save = () => {
    update.mutate(
      {
        ...(statusChanged ? { status } : {}),
        ...(cohortChanged ? { cohort_id: cohortId || null } : {}),
      },
      {
        onSuccess: () => {
          setConfirming(false)
          toast.success('Student updated')
        },
        onError: () => setConfirming(false),
      },
    )
  }

  return (
    <Card>
      <CardHeader title="Manage account" description="Changes are recorded in the audit log." />
      <div className="space-y-4 p-5">
        {update.isError && <Alert>{errorMessage(update.error)}</Alert>}
        <SelectField
          label="Account status"
          value={status}
          onChange={(e) => setStatus(e.target.value as StudentStatus)}
          hint={STATUS_HELP[status]}
        >
          <option value="active">Active</option>
          <option value="suspended">Suspended</option>
          <option value="deactivated">Deactivated</option>
        </SelectField>
        <SelectField label="Cohort" value={cohortId} onChange={(e) => setCohortId(e.target.value)}>
          <option value="">No cohort</option>
          {cohorts.data?.map((c) => (
            <option key={c.id} value={c.id}>
              {c.name}
            </option>
          ))}
        </SelectField>
        <div className="flex justify-end">
          <Button
            disabled={!statusChanged && !cohortChanged}
            loading={update.isPending && !confirming}
            onClick={() => (statusChanged && status !== 'active' ? setConfirming(true) : save())}
          >
            Save changes
          </Button>
        </div>
      </div>
      <Dialog
        open={confirming}
        onClose={() => setConfirming(false)}
        title={status === 'suspended' ? 'Suspend this student?' : 'Deactivate this student?'}
        footer={
          <>
            <Button variant="secondary" onClick={() => setConfirming(false)}>
              Cancel
            </Button>
            <Button variant="danger" loading={update.isPending} onClick={save}>
              {status === 'suspended' ? 'Suspend' : 'Deactivate'}
            </Button>
          </>
        }
      >
        <p className="text-sm text-slate-600">
          <strong className="text-slate-900">{student.full_name}</strong> will be signed out on all{' '}
          {student.active_sessions} active device(s) immediately and won't be able to sign in until
          reactivated. Their learning history is kept.
        </p>
      </Dialog>
    </Card>
  )
}

export default function StudentDetailPage() {
  const { id = '' } = useParams()
  const student = useStudent(id)
  const canManage = useCan('students.manage')

  return (
    <div>
      <Link
        to="/admin/students"
        className="mb-5 inline-flex items-center gap-1.5 text-sm font-medium text-slate-600 hover:text-slate-900"
      >
        <ArrowLeft className="size-4" aria-hidden /> All students
      </Link>

      {student.isPending ? (
        <div className="space-y-4">
          <Skeleton className="h-24 rounded-2xl" />
          <Skeleton className="h-64 rounded-2xl" />
        </div>
      ) : student.isError ? (
        <Alert>{errorMessage(student.error)}</Alert>
      ) : (
        <>
          <div className="mb-6 flex flex-wrap items-center gap-4">
            <span className="grid size-14 place-items-center rounded-2xl bg-gradient-to-br from-brand-500 to-fuchsia-500 text-lg font-bold text-white">
              {initials(student.data.full_name)}
            </span>
            <div className="min-w-0">
              <div className="flex flex-wrap items-center gap-2">
                <h1 className="font-display text-2xl font-bold tracking-tight text-slate-900">
                  {student.data.full_name}
                </h1>
                <StatusBadge status={student.data.status} />
                {student.data.locked_until && (
                  <Badge tone="warning">
                    <Lock className="size-3" aria-hidden /> Locked until{' '}
                    {formatDateTime(student.data.locked_until)}
                  </Badge>
                )}
              </div>
              <p className="text-sm text-slate-600">
                {student.data.email} · <span className="font-mono">{student.data.student_code}</span>
              </p>
            </div>
          </div>

          <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
            <div className="space-y-6 lg:col-span-2">
              <Card>
                <dl className="grid grid-cols-2 gap-x-6 gap-y-5 p-5 sm:grid-cols-4">
                  {[
                    ['Joined', formatDate(student.data.created_at)],
                    ['Last sign-in', timeAgo(student.data.last_login_at)],
                    ['Active devices', String(student.data.active_sessions)],
                    ['Cohort', student.data.cohort?.name ?? '—'],
                  ].map(([label, value]) => (
                    <div key={label}>
                      <dt className="text-xs font-medium text-slate-500">{label}</dt>
                      <dd className="mt-1 text-sm font-semibold text-slate-900">{value}</dd>
                    </div>
                  ))}
                </dl>
              </Card>

              <Card>
                <CardHeader title="Sign-in activity" description="Most recent 10 attempts." />
                {student.data.recent_logins.length === 0 ? (
                  <EmptyState icon={<Lock className="size-6" />} title="No sign-ins yet" />
                ) : (
                  <ul className="divide-y divide-slate-100">
                    {student.data.recent_logins.map((event, i) => (
                      <li key={i} className="flex items-center gap-3 px-5 py-3 text-sm">
                        {event.success ? (
                          <CircleCheck className="size-4 shrink-0 text-emerald-600" aria-label="Succeeded" />
                        ) : (
                          <CircleX className="size-4 shrink-0 text-rose-600" aria-label="Failed" />
                        )}
                        <span className="min-w-0 flex-1">
                          <span className="font-medium text-slate-900">
                            {event.success
                              ? 'Signed in'
                              : (FAILURE_LABELS[event.failure_reason ?? ''] ?? 'Failed sign-in')}
                          </span>
                          <span className="block truncate text-xs text-slate-500">
                            {describeDevice(event.user_agent)}
                            {event.ip_address && ` · ${event.ip_address}`}
                          </span>
                        </span>
                        <time className="text-xs whitespace-nowrap text-slate-500" dateTime={event.created_at}>
                          {formatDateTime(event.created_at)}
                        </time>
                      </li>
                    ))}
                  </ul>
                )}
              </Card>
            </div>

            {canManage && <ManageCard key={student.dataUpdatedAt} student={student.data} />}
          </div>
        </>
      )}
    </div>
  )
}
