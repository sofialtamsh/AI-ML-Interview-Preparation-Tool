import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router'
import { afterEach, describe, expect, it, vi } from 'vitest'

import { adminKeys } from '../../lib/queryClient'
import { REPORT } from '../../test/fixtures/progress'
import OverviewPage from './OverviewPage'

function show(permissions: string[]) {
  const fetch = vi.fn(async (url: string) => {
    if (url.endsWith('/admin/overview')) return Response.json({ students: null, active_admins: null })
    if (url.includes('/admin/analytics')) return Response.json(REPORT)
    return Response.json({ detail: 'Not found' }, { status: 404 })
  })
  vi.stubGlobal('fetch', fetch)
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  client.setQueryData(adminKeys.me, { id: 'a', email: 'a@x.com', full_name: 'Asha Admin', roles: [], permissions })
  render(
    <QueryClientProvider client={client}>
      <MemoryRouter>
        <OverviewPage />
      </MemoryRouter>
    </QueryClientProvider>,
  )
  return fetch
}

afterEach(() => vi.unstubAllGlobals())

describe('admin overview', () => {
  it('shows learning progress, completion, performance and who needs attention', async () => {
    show(['analytics.view'])
    expect(await screen.findByRole('heading', { name: 'Learning' })).toBeInTheDocument()
    expect(await screen.findByText('31%')).toBeInTheDocument() // average path completion
    expect(screen.getByText('12 h 30 min')).toBeInTheDocument()
    expect(screen.getByText('68%')).toBeInTheDocument() // quiz average
    expect(screen.getByText('6.2/10')).toBeInTheDocument()
    expect(screen.getByText('Completion by domain')).toBeInTheDocument()
    expect(screen.getByText('5/20 finished · quiz 41%')).toBeInTheDocument()
    expect(screen.getByRole('link', { name: /See who/ })).toHaveAttribute('href', '/admin/students?attention=any')
    expect(screen.getByRole('link', { name: /Open analytics/ })).toHaveAttribute('href', '/admin/analytics')
  })

  it('leaves learning out for admins without analytics access', async () => {
    const fetch = show([])
    expect(await screen.findByText('Your access')).toBeInTheDocument()
    expect(screen.queryByRole('heading', { name: 'Learning' })).not.toBeInTheDocument()
    expect(fetch).not.toHaveBeenCalledWith(expect.stringContaining('/admin/analytics'), expect.anything())
  })
})
