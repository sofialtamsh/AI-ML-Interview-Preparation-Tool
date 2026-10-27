import { useState, type FormEvent } from 'react'
import { useNavigate } from 'react-router'

import { AuthLayout } from '../../components/AuthLayout'
import { PasswordStrengthMeter } from '../../components/PasswordStrengthMeter'
import { Button } from '../../components/ui/Button'
import { Alert } from '../../components/ui/Feedback'
import { PasswordField } from '../../components/ui/Field'
import { errorMessage } from '../../lib/api'
import { PASSWORD_MIN_LENGTH } from '../../lib/password'
import { useAdminChangePassword, useAdminLogout, useCurrentAdmin } from '../api'

export default function ChangePasswordPage() {
  const admin = useCurrentAdmin()
  const [current, setCurrent] = useState('')
  const [next, setNext] = useState('')
  const change = useAdminChangePassword()
  const logout = useAdminLogout()
  const navigate = useNavigate()

  const submit = (event: FormEvent) => {
    event.preventDefault()
    change.mutate(
      { current_password: current, new_password: next },
      { onSuccess: () => navigate('/admin', { replace: true }) },
    )
  }

  return (
    <AuthLayout
      variant="admin"
      title="Set your own password"
      subtitle={`Hi ${admin.full_name.split(' ')[0]}, you signed in with a temporary password. Choose your own to continue.`}
      footer={
        <button
          type="button"
          className="font-semibold text-slate-700 hover:text-slate-900"
          onClick={() => logout.mutate(undefined, { onSettled: () => navigate('/admin/login') })}
        >
          Sign out instead
        </button>
      }
    >
      <form onSubmit={submit} className="space-y-5" noValidate>
        {change.isError && <Alert>{errorMessage(change.error)}</Alert>}
        <PasswordField
          label="Temporary password"
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
        <Button
          type="submit"
          size="lg"
          className="w-full"
          loading={change.isPending}
          disabled={!current || next.length < PASSWORD_MIN_LENGTH}
        >
          Save and continue
        </Button>
      </form>
    </AuthLayout>
  )
}
