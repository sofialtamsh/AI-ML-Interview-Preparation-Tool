import { describe, expect, it } from 'vitest'

import { ADMIN_NAV, SETTINGS_TABS, visibleFor } from './nav'

const labels = (items: { label: string }[]) => items.map((i) => i.label)

describe('admin navigation', () => {
  it('shows only the overview to an admin without relevant permissions', () => {
    expect(labels(visibleFor(ADMIN_NAV, ['content.review']))).toEqual(['Overview'])
  })

  it('shows sections matching any held permission', () => {
    expect(labels(visibleFor(ADMIN_NAV, ['students.view', 'audit.view']))).toEqual([
      'Overview',
      'Students',
      'System settings',
    ])
  })

  it('filters settings tabs independently', () => {
    expect(labels(visibleFor(SETTINGS_TABS, ['roles.manage']))).toEqual(['Roles & permissions'])
    expect(labels(visibleFor(SETTINGS_TABS, ['admins.manage']))).toEqual([
      'Admins',
      'Roles & permissions',
    ])
  })

  it('opens system settings to admins who can only see AI spend', () => {
    expect(labels(visibleFor(ADMIN_NAV, ['ai_usage.view']))).toEqual(['Overview', 'System settings'])
    expect(labels(visibleFor(SETTINGS_TABS, ['ai_usage.view']))).toEqual(['AI usage'])
  })
})
