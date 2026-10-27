import { Laptop, Smartphone } from 'lucide-react'
import { useState, type FormEvent } from 'react'
import { useNavigate } from 'react-router'

import { PasswordStrengthMeter } from '../../components/PasswordStrengthMeter'
import { Button } from '../../components/ui/Button'
import { Alert, Badge, Card, CardHeader, PageHeader, Skeleton } from '../../components/ui/Feedback'
import { PasswordField, TextField } from '../../components/ui/Field'
import { useToast } from '../../components/ui/Toast'
import { errorMessage } from '../../lib/api'
import { describeDevice, formatDate, isMobileDevice, timeAgo } from '../../lib/format'
import { PASSWORD_MIN_LENGTH } from '../../lib/password'
import {
  useChangePassword,
  useCurrentStudent,
  useRevokeOtherSessions,
  useRevokeSession,
  useSessions,
  useUpdateProfile,
} from '../api'

function ProfileCard() {
  const student = useCurrentStudent()
  const [name, setName] = useState(student.full_name)
  const update = useUpdateProfile()
  const toast = useToast()

  const submit = (event: FormEvent) => {
    event.preventDefault()
    update.mutate({ full_name: name.trim() }, { onSuccess: () => toast.success('Profile saved') })
  }

  return (
    <Card>
      <CardHeader title="Profile" description="How you appear on the platform." />
      <form onSubmit={submit} className="space-y-4 p-5">
        {update.isError && <Alert>{errorMessage(update.error)}</Alert>}
        <TextField
          label="Full name"
          autoComplete="name"
          value={name}
          onChange={(e) => setName(e.target.value)}
        />
        <TextField label="Email" value={student.email} disabled hint="Used to sign in." />
        <div className="grid grid-cols-2 gap-4">
          <TextField label="Student ID" value={student.student_code} disabled />
          <TextField label="Joined" value={formatDate(student.created_at)} disabled />
        </div>
        <div className="flex justify-end">
          <Button
            type="submit"
            loading={update.isPending}
            disabled={name.trim().length < 2 || name.trim() === student.full_name}
          >
            Save changes
          </Button>
        </div>
      </form>
    </Card>
  )
}

function PasswordCard() {
  const [current, setCurrent] = useState('')
  const [next, setNext] = useState('')
  const change = useChangePassword()
  const toast = useToast()

  const submit = (event: FormEvent) => {
    event.preventDefault()
    change.mutate(
      { current_password: current, new_password: next },
      {
        onSuccess: (data) => {
          toast.success(data.message)
          setCurrent('')
          setNext('')
        },
      },
    )
  }

  return (
    <Card>
      <CardHeader
        title="Password"
        description="Changing it signs you out everywhere except this device."
      />
      <form onSubmit={submit} className="space-y-4 p-5">
        {change.isError && <Alert>{errorMessage(change.error)}</Alert>}
        <PasswordField
          label="Current password"
          autoComplete="current-password"
          value={current}
          onChange={(e) => setCurrent(e.target.value)}
        />
        <div>
          <PasswordField
            label="New password"
            autoComplete="new-password"
            value={next}
            onChange={(e) => setNext(e.target.value)}
          />
          <PasswordStrengthMeter password={next} />
        </div>
        <div className="flex justify-end">
          <Button
            type="submit"
            loading={change.isPending}
            disabled={!current || next.length < PASSWORD_MIN_LENGTH}
          >
            Update password
          </Button>
        </div>
      </form>
    </Card>
  )
}

function DevicesCard() {
  const sessions = useSessions()
  const revoke = useRevokeSession()
  const revokeOthers = useRevokeOtherSessions()
  const toast = useToast()
  const navigate = useNavigate()
  const others = sessions.data?.filter((s) => !s.current).length ?? 0

  return (
    <Card className="lg:col-span-2">
      <CardHeader
        title="Signed-in devices"
        description="Your progress follows you to every device you sign in on."
        action={
          others > 0 && (
            <Button
              variant="secondary"
              size="sm"
              loading={revokeOthers.isPending}
              onClick={() =>
                revokeOthers.mutate(undefined, { onSuccess: (data) => toast.success(data.message) })
              }
            >
              Sign out other devices
            </Button>
          )
        }
      />
      {sessions.isPending ? (
        <div className="space-y-3 p-5">
          <Skeleton className="h-12" />
          <Skeleton className="h-12" />
        </div>
      ) : sessions.isError ? (
        <div className="p-5">
          <Alert>{errorMessage(sessions.error)}</Alert>
        </div>
      ) : (
        <ul className="divide-y divide-slate-100">
          {sessions.data.map((session) => {
            const Icon = isMobileDevice(session.user_agent) ? Smartphone : Laptop
            return (
              <li key={session.id} className="flex items-center gap-4 px-5 py-4">
                <span className="grid size-10 shrink-0 place-items-center rounded-xl bg-slate-100 text-slate-600">
                  <Icon className="size-5" aria-hidden />
                </span>
                <div className="min-w-0 flex-1">
                  <p className="flex flex-wrap items-center gap-2 text-sm font-medium text-slate-900">
                    {describeDevice(session.user_agent)}
                    {session.current && <Badge tone="success">This device</Badge>}
                  </p>
                  <p className="text-xs text-slate-500">
                    Active {timeAgo(session.last_seen_at)} · signed in{' '}
                    {formatDate(session.created_at)}
                    {session.ip_address && ` · ${session.ip_address}`}
                  </p>
                </div>
                <Button
                  variant="ghost"
                  size="sm"
                  disabled={revoke.isPending}
                  onClick={() =>
                    revoke.mutate(session, {
                      onSuccess: () => {
                        if (session.current) navigate('/login')
                        else toast.success('Device signed out')
                      },
                      onError: (error) => toast.error(errorMessage(error)),
                    })
                  }
                >
                  Sign out
                </Button>
              </li>
            )
          })}
        </ul>
      )}
    </Card>
  )
}

export default function ProfilePage() {
  return (
    <div className="animate-fade-up">
      <PageHeader title="My profile" description="Manage your details, password and devices." />
      <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
        <ProfileCard />
        <PasswordCard />
        <DevicesCard />
      </div>
    </div>
  )
}
