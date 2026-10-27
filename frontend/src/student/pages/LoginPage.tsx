import { useState, type FormEvent } from 'react'
import { Link, useLocation, useNavigate } from 'react-router'

import { AuthLayout } from '../../components/AuthLayout'
import { Button } from '../../components/ui/Button'
import { Alert } from '../../components/ui/Feedback'
import { PasswordField, TextField } from '../../components/ui/Field'
import { errorMessage } from '../../lib/api'
import { useStudentLogin } from '../api'

export default function LoginPage() {
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const login = useStudentLogin()
  const navigate = useNavigate()
  const location = useLocation()
  const from = (location.state as { from?: string } | null)?.from ?? '/app'

  const submit = (event: FormEvent) => {
    event.preventDefault()
    login.mutate({ email, password }, { onSuccess: () => navigate(from, { replace: true }) })
  }

  return (
    <AuthLayout
      title="Welcome back"
      subtitle="Sign in to pick up right where you left off."
      footer={
        <>
          New here?{' '}
          <Link to="/register" className="font-semibold text-brand-700 hover:text-brand-800">
            Create a free account
          </Link>
        </>
      }
    >
      <form onSubmit={submit} className="space-y-5" noValidate>
        {login.isError && <Alert>{errorMessage(login.error)}</Alert>}
        <TextField
          label="Email"
          type="email"
          autoComplete="email"
          required
          value={email}
          onChange={(e) => setEmail(e.target.value)}
        />
        <PasswordField
          label="Password"
          autoComplete="current-password"
          required
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          labelAction={
            <Link
              to="/forgot-password"
              className="text-xs font-semibold text-brand-700 hover:text-brand-800"
            >
              Forgot password?
            </Link>
          }
        />
        <Button
          type="submit"
          variant="glow"
          size="lg"
          className="w-full"
          loading={login.isPending}
          disabled={!email || !password}
        >
          Sign in
        </Button>
      </form>
    </AuthLayout>
  )
}
