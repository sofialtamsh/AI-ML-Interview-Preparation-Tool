import { ShieldX, TriangleAlert } from 'lucide-react'
import type { ReactNode } from 'react'
import { Navigate, Outlet, useLocation } from 'react-router'

import { Button } from '../components/ui/Button'
import { EmptyState, FullPageLoader } from '../components/ui/Feedback'
import { errorMessage } from '../lib/api'
import { useAdminMe, useCan } from './api'

/** Admin-only area. Sends anyone else to the admin sign-in, and forces a temporary password
 * to be replaced before anything else (the API enforces the same rule). */
export function RequireAdmin({
  children,
  passwordChangePage = false,
}: {
  children?: ReactNode
  passwordChangePage?: boolean
}) {
  const { data: me, isPending, error, refetch } = useAdminMe()
  const location = useLocation()

  if (isPending) return <FullPageLoader />
  if (error) {
    return (
      <div className="grid min-h-dvh place-items-center">
        <EmptyState
          icon={<TriangleAlert className="size-6" />}
          title="We couldn't load your admin session"
          action={<Button onClick={() => refetch()}>Try again</Button>}
        >
          {errorMessage(error)}
        </EmptyState>
      </div>
    )
  }
  if (!me) {
    return (
      <Navigate to="/admin/login" replace state={{ from: location.pathname + location.search }} />
    )
  }
  if (me.must_change_password && !passwordChangePage) {
    return <Navigate to="/admin/change-password" replace />
  }
  if (!me.must_change_password && passwordChangePage) return <Navigate to="/admin" replace />
  return children ?? <Outlet />
}

export function RequirePermission({ anyOf, children }: { anyOf: string[]; children: ReactNode }) {
  const allowed = useCan(...anyOf)
  if (allowed) return children
  return (
    <EmptyState icon={<ShieldX className="size-6" />} title="You don't have access to this page">
      Your admin role doesn't include this area. Ask a Super Admin if you need access.
    </EmptyState>
  )
}
