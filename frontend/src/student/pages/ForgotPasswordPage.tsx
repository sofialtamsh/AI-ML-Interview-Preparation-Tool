import { MailCheck } from 'lucide-react'
import { useState, type FormEvent } from 'react'
import { Link } from 'react-router'

import { AuthLayout } from '../../components/AuthLayout'
import { Button } from '../../components/ui/Button'
import { Alert } from '../../components/ui/Feedback'
import { TextField } from '../../components/ui/Field'
import { errorMessage } from '../../lib/api'
import { useRequestPasswordReset } from '../api'

export default function ForgotPasswordPage() {
  const [email, setEmail] = useState('')
  const request = useRequestPasswordReset()

  const submit = (event: FormEvent) => {
    event.preventDefault()
    request.mutate(email)
  }

  return (
    <AuthLayout
      title="Reset your password"
      subtitle="Enter the email you signed up with and we'll send you a reset link."
      footer={
        <Link to="/login" className="font-semibold text-brand-700 hover:text-brand-800">
          ← Back to sign in
        </Link>
      }
    >
      {request.isSuccess ? (
        <div className="animate-pop rounded-2xl bg-emerald-50 p-5 ring-1 ring-emerald-200">
          <MailCheck className="size-6 text-emerald-600" aria-hidden />
          <p className="mt-3 font-semibold text-emerald-900">Check your inbox</p>
          <p className="mt-1 text-sm text-emerald-800">{request.data.message}</p>
          <p className="mt-3 text-xs text-emerald-700">
            The link expires in 30 minutes and works once.
          </p>
        </div>
      ) : (
        <form onSubmit={submit} className="space-y-5" noValidate>
          {request.isError && <Alert>{errorMessage(request.error)}</Alert>}
          <TextField
            label="Email"
            type="email"
            autoComplete="email"
            required
            value={email}
            onChange={(e) => setEmail(e.target.value)}
          />
          <Button
            type="submit"
            size="lg"
            className="w-full"
            loading={request.isPending}
            disabled={!email.includes('@')}
          >
            Send reset link
          </Button>
        </form>
      )}
    </AuthLayout>
  )
}
