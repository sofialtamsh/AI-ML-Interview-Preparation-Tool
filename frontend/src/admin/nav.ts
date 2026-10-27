import { Database, GraduationCap, LayoutDashboard, Settings, type LucideIcon } from 'lucide-react'

export type NavItem = {
  to: string
  label: string
  icon: LucideIcon
  end?: boolean
  /** Shown if the admin holds any of these permissions; omitted = every admin. */
  anyOf?: string[]
}

// Only modules that work today are listed. Each later phase adds its own entry
// (agents, intelligence, taxonomy, studio, review, analytics, ...).
export const ADMIN_NAV: NavItem[] = [
  { to: '/admin', label: 'Overview', icon: LayoutDashboard, end: true },
  { to: '/admin/students', label: 'Students', icon: GraduationCap, anyOf: ['students.view'] },
  { to: '/admin/sources', label: 'Interview sources', icon: Database, anyOf: ['sources.view'] },
  {
    to: '/admin/settings',
    label: 'System settings',
    icon: Settings,
    anyOf: ['admins.manage', 'roles.manage', 'audit.view', 'ai_usage.view'],
  },
]

export type SettingsTab = { to: string; label: string; anyOf: string[] }

export const SETTINGS_TABS: SettingsTab[] = [
  { to: 'admins', label: 'Admins', anyOf: ['admins.manage'] },
  { to: 'roles', label: 'Roles & permissions', anyOf: ['admins.manage', 'roles.manage'] },
  { to: 'audit', label: 'Audit log', anyOf: ['audit.view'] },
  { to: 'usage', label: 'AI usage', anyOf: ['ai_usage.view'] },
]

export function visibleFor<T extends { anyOf?: string[] }>(items: T[], permissions: string[]): T[] {
  return items.filter((item) => !item.anyOf || item.anyOf.some((p) => permissions.includes(p)))
}
