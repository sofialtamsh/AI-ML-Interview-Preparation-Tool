import { useState, type FormEvent } from 'react'
import { Link, useNavigate } from 'react-router'

import { AuthLayout } from '../../components/AuthLayout'
import { PasswordStrengthMeter } from '../../components/PasswordStrengthMeter'
import { Button } from '../../components/ui/Button'
import { Alert } from '../../components/ui/Feedback'
import { PasswordField, TextField } from '../../components/ui/Field'
import { ApiError, errorMessage } from '../../lib/api'
import { PASSWORD_MIN_LENGTH } from '../../lib/password'
import { useStudentRegister } from '../api'

export default function RegisterPage() {
  const [fullName, setFullName] = useState('')
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const register = useStudentRegister()
  const navigate = useNavigate()
  const fieldErrors = register.error instanceof ApiError ? register.error.fieldErrors : {}

  const canSubmit =
    fullName.trim().length >= 2 && email.includes('@') && password.length >= PASSWORD_MIN_LENGTH

  const submit = (event: FormEvent) => {
    event.preventDefault()
    register.mutate(
      { full_name: fullName.trim(), email, password },
      { onSuccess: () => navigate('/app', { replace: true }) },
    )
  }

  return (
    <AuthLayout
      title="Create your account"
      subtitle="Your progress is saved to your account, on every device."
      footer={
        <>
          Already have an account?{' '}
          <Link to="/login" className="font-semibold text-brand-700 hover:text-brand-800">
            Sign in
          </Link>
        </>
      }
    >
      <form onSubmit={submit} className="space-y-5" noValidate>
        {register.isError && Object.keys(fieldErrors).length === 0 && (
          <Alert>{errorMessage(register.error)}</Alert>
        )}
        <TextField
          label="Full name"
          autoComplete="name"
          required
          value={fullName}
          onChange={(e) => setFullName(e.target.value)}
          error={fieldErrors.full_name}
        />
        <TextField
          label="Email"
          type="email"
          autoComplete="email"
          required
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          error={fieldErrors.email}
        />
        <div>
          <PasswordField
            label="Password"
            autoComplete="new-password"
            required
            minLength={PASSWORD_MIN_LENGTH}
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            error={fieldErrors.password}
          />
          {!fieldErrors.password && <PasswordStrengthMeter password={password} />}
        </div>
        <Button
          type="submit"
          variant="glow"
          size="lg"
          className="w-full"
          loading={register.isPending}
          disabled={!canSubmit}
        >
          Create account
        </Button>
      </form>
    </AuthLayout>
  )
}
