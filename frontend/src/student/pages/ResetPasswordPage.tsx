import { useState, type FormEvent } from 'react'
import { Link, useSearchParams } from 'react-router'

import { AuthLayout } from '../../components/AuthLayout'
import { PasswordStrengthMeter } from '../../components/PasswordStrengthMeter'
import { Button, ButtonLink } from '../../components/ui/Button'
import { Alert } from '../../components/ui/Feedback'
import { PasswordField } from '../../components/ui/Field'
import { errorMessage } from '../../lib/api'
import { PASSWORD_MIN_LENGTH } from '../../lib/password'
import { useConfirmPasswordReset } from '../api'

export default function ResetPasswordPage() {
  const [params] = useSearchParams()
  const token = params.get('token') ?? ''
  const [password, setPassword] = useState('')
  const confirm = useConfirmPasswordReset()

  const submit = (event: FormEvent) => {
    event.preventDefault()
    confirm.mutate({ token, new_password: password })
  }

  return (
    <AuthLayout title="Choose a new password" subtitle="You'll be signed out on all devices.">
      {!token ? (
        <Alert>
          This reset link is incomplete.{' '}
          <Link to="/forgot-password" className="font-semibold underline">
            Request a new one
          </Link>
          .
        </Alert>
      ) : confirm.isSuccess ? (
        <div className="space-y-5">
          <Alert tone="success">{confirm.data.message}</Alert>
          <ButtonLink to="/login" size="lg" variant="glow" className="w-full">
            Sign in
          </ButtonLink>
        </div>
      ) : (
        <form onSubmit={submit} className="space-y-5" noValidate>
          {confirm.isError && (
            <Alert>
              {errorMessage(confirm.error)}{' '}
              <Link to="/forgot-password" className="font-semibold underline">
                Get a new link
              </Link>
            </Alert>
          )}
          <div>
            <PasswordField
              label="New password"
              autoComplete="new-password"
              required
              value={password}
              onChange={(e) => setPassword(e.target.value)}
            />
            <PasswordStrengthMeter password={password} />
          </div>
          <Button
            type="submit"
            size="lg"
            className="w-full"
            loading={confirm.isPending}
            disabled={password.length < PASSWORD_MIN_LENGTH}
          >
            Update password
          </Button>
        </form>
      )}
    </AuthLayout>
  )
}
