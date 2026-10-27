import { Navigate, NavLink, Outlet, useLocation } from 'react-router'

import { PageHeader } from '../../../components/ui/Feedback'
import { cn } from '../../../lib/cn'
import { useCurrentAdmin } from '../../api'
import { SETTINGS_TABS, visibleFor } from '../../nav'

export default function SettingsLayout() {
  const admin = useCurrentAdmin()
  const tabs = visibleFor(SETTINGS_TABS, admin.permissions)
  const location = useLocation()

  if (location.pathname.replace(/\/$/, '') === '/admin/settings' && tabs[0]) {
    return <Navigate to={tabs[0].to} replace />
  }

  return (
    <div>
      <PageHeader title="System settings" description="Admin accounts, roles, the audit trail and AI spend." />
      <nav aria-label="Settings" className="mb-6 flex flex-wrap gap-1 rounded-2xl bg-white p-1.5 shadow-sm ring-1 ring-slate-200/80 sm:inline-flex">
        {tabs.map((tab) => (
          <NavLink
            key={tab.to}
            to={tab.to}
            className={({ isActive }) =>
              cn(
                'rounded-xl px-4 py-2 text-sm font-medium whitespace-nowrap transition',
                isActive ? 'bg-slate-900 text-white' : 'text-slate-600 hover:bg-slate-100',
              )
            }
          >
            {tab.label}
          </NavLink>
        ))}
      </nav>
      <Outlet />
    </div>
  )
}
