import { LogOut, Menu, X } from 'lucide-react'
import { Suspense, useState } from 'react'
import { Link, NavLink, Outlet, useLocation, useNavigate } from 'react-router'

import { Logo } from '../components/Logo'
import { Spinner } from '../components/ui/Feedback'
import { cn } from '../lib/cn'
import { initials } from '../lib/format'
import { useAdminLogout, useCurrentAdmin } from './api'
import { ADMIN_NAV, visibleFor } from './nav'

function Sidebar({ onNavigate }: { onNavigate?: () => void }) {
  const admin = useCurrentAdmin()
  const items = visibleFor(ADMIN_NAV, admin.permissions)
  return (
    <nav aria-label="Admin" className="flex flex-col gap-1 p-3">
      {items.map((item) => (
        <NavLink
          key={item.to}
          to={item.to}
          end={item.end}
          onClick={onNavigate}
          className={({ isActive }) =>
            cn(
              'group flex items-center gap-3 rounded-xl px-3 py-2.5 text-sm font-medium transition',
              isActive
                ? 'bg-white/10 text-white ring-1 ring-white/10'
                : 'text-slate-400 hover:bg-white/5 hover:text-white',
            )
          }
        >
          <item.icon className="size-[18px]" aria-hidden />
          {item.label}
        </NavLink>
      ))}
    </nav>
  )
}

export function AdminLayout() {
  const admin = useCurrentAdmin()
  const logout = useAdminLogout()
  const navigate = useNavigate()
  const location = useLocation()
  const [menuOpen, setMenuOpen] = useState(false)

  const signOut = () => logout.mutate(undefined, { onSettled: () => navigate('/admin/login') })

  return (
    <div className="min-h-dvh bg-slate-100/70 lg:grid lg:grid-cols-[260px_minmax(0,1fr)]">
      {/* Desktop sidebar */}
      <aside className="sticky top-0 hidden h-dvh flex-col bg-slate-950 lg:flex">
        <Link to="/admin" className="m-3 rounded-xl px-2 py-3">
          <Logo tone="light" suffix="Admin console" />
        </Link>
        <Sidebar />
        <div className="mt-auto border-t border-white/10 p-4">
          <div className="flex items-center gap-3">
            <span className="grid size-9 shrink-0 place-items-center rounded-full bg-gradient-to-br from-brand-500 to-fuchsia-500 text-xs font-bold text-white">
              {initials(admin.full_name)}
            </span>
            <div className="min-w-0 flex-1">
              <p className="truncate text-sm font-medium text-white">{admin.full_name}</p>
              <p className="truncate text-xs text-slate-400">
                {admin.roles.map((r) => r.name).join(', ')}
              </p>
            </div>
            <button
              type="button"
              onClick={signOut}
              className="rounded-lg p-2 text-slate-400 transition hover:bg-white/10 hover:text-white"
              aria-label="Sign out"
              title="Sign out"
            >
              <LogOut className="size-4" />
            </button>
          </div>
        </div>
      </aside>

      {/* Mobile header + drawer */}
      <header className="sticky top-0 z-30 flex h-14 items-center justify-between bg-slate-950 px-4 lg:hidden">
        <Link to="/admin" className="rounded-lg">
          <Logo tone="light" />
        </Link>
        <button
          type="button"
          onClick={() => setMenuOpen(true)}
          className="rounded-lg p-2 text-slate-300 hover:bg-white/10"
          aria-label="Open menu"
          aria-expanded={menuOpen}
        >
          <Menu className="size-5" />
        </button>
      </header>
      {menuOpen && (
        <div className="fixed inset-0 z-40 lg:hidden" role="dialog" aria-modal="true" aria-label="Menu">
          <button
            type="button"
            className="absolute inset-0 bg-slate-950/50 backdrop-blur-sm"
            onClick={() => setMenuOpen(false)}
            aria-label="Close menu"
          />
          <div className="absolute inset-y-0 left-0 flex w-72 animate-fade-up flex-col bg-slate-950">
            <div className="flex items-center justify-between p-4">
              <Logo tone="light" />
              <button
                type="button"
                onClick={() => setMenuOpen(false)}
                className="rounded-lg p-2 text-slate-300 hover:bg-white/10"
                aria-label="Close menu"
              >
                <X className="size-5" />
              </button>
            </div>
            <Sidebar onNavigate={() => setMenuOpen(false)} />
            <button
              type="button"
              onClick={signOut}
              className="m-4 mt-auto flex items-center gap-2 rounded-xl px-3 py-2.5 text-sm text-slate-300 hover:bg-white/10"
            >
              <LogOut className="size-4" aria-hidden /> Sign out
            </button>
          </div>
        </div>
      )}

      <main className="min-w-0 px-4 py-6 sm:px-8 sm:py-8">
        <div key={location.pathname.split('/')[2] ?? ''} className="mx-auto max-w-7xl animate-fade-up">
          <Suspense
            fallback={
              <div className="grid h-64 place-items-center">
                <Spinner className="size-6 text-brand-500" />
              </div>
            }
          >
            <Outlet />
          </Suspense>
        </div>
      </main>
    </div>
  )
}
