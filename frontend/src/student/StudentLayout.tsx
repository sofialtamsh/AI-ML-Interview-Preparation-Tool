import { LayoutDashboard, LogOut, UserRound } from 'lucide-react'
import { Suspense } from 'react'
import { Link, NavLink, Outlet, useNavigate } from 'react-router'

import { Logo } from '../components/Logo'
import { FullPageLoader } from '../components/ui/Feedback'
import { useToast } from '../components/ui/Toast'
import { cn } from '../lib/cn'
import { initials } from '../lib/format'
import { useCurrentStudent, useStudentLogout } from './api'

// Only sections that work today are listed; learning sections join as they ship.
const NAV = [
  { to: '/app', label: 'Dashboard', icon: LayoutDashboard, end: true },
  { to: '/app/profile', label: 'My profile', icon: UserRound, end: false },
]

export function StudentLayout() {
  const student = useCurrentStudent()
  const logout = useStudentLogout()
  const navigate = useNavigate()
  const toast = useToast()

  const signOut = () =>
    logout.mutate(undefined, {
      onSuccess: () => {
        toast.success('Signed out. See you soon!')
        navigate('/login')
      },
    })

  return (
    <div className="min-h-dvh bg-[radial-gradient(ellipse_at_top,_var(--color-brand-50),_transparent_55%)] pb-20 sm:pb-0">
      <header className="sticky top-0 z-30 border-b border-slate-200/70 bg-white/75 backdrop-blur-xl">
        <div className="mx-auto flex h-16 max-w-6xl items-center gap-6 px-4 sm:px-6">
          <Link to="/app" className="rounded-lg">
            <Logo />
          </Link>
          <nav aria-label="Main" className="hidden flex-1 items-center gap-1 sm:flex">
            {NAV.map((item) => (
              <NavLink
                key={item.to}
                to={item.to}
                end={item.end}
                className={({ isActive }) =>
                  cn(
                    'rounded-xl px-3.5 py-2 text-sm font-medium transition',
                    isActive
                      ? 'bg-brand-600 text-white shadow-sm shadow-brand-600/25'
                      : 'text-slate-600 hover:bg-slate-100 hover:text-slate-900',
                  )
                }
              >
                {item.label}
              </NavLink>
            ))}
          </nav>
          <div className="ml-auto flex items-center gap-2">
            <span
              className="grid size-9 place-items-center rounded-full bg-gradient-to-br from-brand-500 to-fuchsia-500 text-xs font-bold text-white"
              title={student.full_name}
              aria-hidden
            >
              {initials(student.full_name)}
            </span>
            <button
              type="button"
              onClick={signOut}
              disabled={logout.isPending}
              className="inline-flex items-center gap-1.5 rounded-xl px-3 py-2 text-sm font-medium text-slate-600 transition hover:bg-slate-100 hover:text-slate-900"
            >
              <LogOut className="size-4" aria-hidden />
              <span className="hidden sm:inline">Sign out</span>
            </button>
          </div>
        </div>
      </header>

      <main className="mx-auto max-w-6xl px-4 py-8 sm:px-6 sm:py-10">
        <Suspense fallback={<FullPageLoader />}>
          <Outlet />
        </Suspense>
      </main>

      <nav
        aria-label="Main"
        className="fixed inset-x-0 bottom-0 z-30 grid grid-cols-2 border-t border-slate-200 bg-white/90 pb-[env(safe-area-inset-bottom)] backdrop-blur-xl sm:hidden"
      >
        {NAV.map((item) => (
          <NavLink
            key={item.to}
            to={item.to}
            end={item.end}
            className={({ isActive }) =>
              cn(
                'flex flex-col items-center gap-0.5 py-2.5 text-[11px] font-medium transition',
                isActive ? 'text-brand-600' : 'text-slate-500',
              )
            }
          >
            <item.icon className="size-5" aria-hidden />
            {item.label}
          </NavLink>
        ))}
      </nav>
    </div>
  )
}
