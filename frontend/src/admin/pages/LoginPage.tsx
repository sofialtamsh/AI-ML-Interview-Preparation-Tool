import { useState, type FormEvent } from 'react'
import { Navigate, useLocation, useNavigate } from 'react-router'

import { AuthLayout } from '../../components/AuthLayout'
import { Button } from '../../components/ui/Button'
import { Alert, FullPageLoader } from '../../components/ui/Feedback'
import { PasswordField, TextField } from '../../components/ui/Field'
import { errorMessage } from '../../lib/api'
import { useAdminLogin, useAdminMe } from '../api'

export default function AdminLoginPage() {
  const me = useAdminMe()
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const login = useAdminLogin()
  const navigate = useNavigate()
  const location = useLocation()
  const from = (location.state as { from?: string } | null)?.from ?? '/admin'

  if (me.isPending) return <FullPageLoader />
  // Already signed in when arriving here; after a fresh sign-in, onSuccess below navigates.
  if (me.data && login.isIdle) return <Navigate to="/admin" replace />

  const submit = (event: FormEvent) => {
    event.preventDefault()
    login.mutate(
      { email, password },
      {
        onSuccess: (admin) =>
          navigate(admin.must_change_password ? '/admin/change-password' : from, { replace: true }),
      },
    )
  }

  return (
    <AuthLayout
      variant="admin"
      title="Admin sign in"
      subtitle="Use the credentials issued to you by a platform administrator."
    >
      <form onSubmit={submit} className="space-y-5" noValidate>
        {login.isError && <Alert>{errorMessage(login.error)}</Alert>}
        <TextField
          label="Work email"
          type="email"
          autoComplete="username"
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
        />
        <Button
          type="submit"
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
