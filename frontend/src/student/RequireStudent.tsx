import { TriangleAlert } from 'lucide-react'
import type { ReactNode } from 'react'
import { Navigate, Outlet, useLocation } from 'react-router'

import { Button } from '../components/ui/Button'
import { EmptyState, FullPageLoader } from '../components/ui/Feedback'
import { errorMessage } from '../lib/api'
import { useStudentMe } from './api'

/** Renders its content only for a signed-in student; otherwise sends them to sign in. */
export function RequireStudent({ children }: { children?: ReactNode }) {
  const { data: me, isPending, error, refetch } = useStudentMe()
  const location = useLocation()

  if (isPending) return <FullPageLoader />
  if (error) {
    return (
      <div className="grid min-h-dvh place-items-center">
        <EmptyState
          icon={<TriangleAlert className="size-6" />}
          title="We couldn't load your account"
          action={<Button onClick={() => refetch()}>Try again</Button>}
        >
          {errorMessage(error)}
        </EmptyState>
      </div>
    )
  }
  if (!me) {
    return <Navigate to="/login" replace state={{ from: location.pathname + location.search }} />
  }
  return children ?? <Outlet />
}

/** For sign-in/sign-up pages: a student who is already signed in goes to the dashboard. */
export function RedirectIfStudent({ children }: { children: ReactNode }) {
  const { data: me, isPending } = useStudentMe()
  const location = useLocation()
  if (isPending) return <FullPageLoader />
  if (me) {
    const from = (location.state as { from?: string } | null)?.from
    return <Navigate to={from ?? '/app'} replace />
  }
  return children
}
