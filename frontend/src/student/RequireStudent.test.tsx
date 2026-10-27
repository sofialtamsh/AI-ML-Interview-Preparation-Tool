import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, screen } from '@testing-library/react'
import { createMemoryRouter, RouterProvider } from 'react-router'
import { afterEach, describe, expect, it, vi } from 'vitest'

import { RedirectIfStudent, RequireStudent } from './RequireStudent'

const ME = {
  id: 's1',
  student_code: 'STU-001001',
  full_name: 'Asha Rao',
  email: 'asha@example.com',
  status: 'active',
  cohort_name: null,
  created_at: '2026-10-01T00:00:00Z',
  last_login_at: null,
}

function respondToMe(status: number) {
  vi.stubGlobal(
    'fetch',
    vi.fn().mockResolvedValue(
      new Response(JSON.stringify(status === 200 ? ME : { detail: 'Not authenticated.' }), {
        status,
      }),
    ),
  )
}

function renderAt(path: string) {
  const router = createMemoryRouter(
    [
      { path: '/login', element: <RedirectIfStudent><p>Sign-in page</p></RedirectIfStudent> },
      { path: '/app', element: <RequireStudent><p>Dashboard</p></RequireStudent> },
    ],
    { initialEntries: [path] },
  )
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  render(
    <QueryClientProvider client={client}>
      <RouterProvider router={router} />
    </QueryClientProvider>,
  )
}

afterEach(() => vi.unstubAllGlobals())

describe('student route guard', () => {
  it('sends signed-out visitors to the sign-in page', async () => {
    respondToMe(401)
    renderAt('/app')
    expect(await screen.findByText('Sign-in page')).toBeInTheDocument()
  })

  it('renders the protected page for a signed-in student', async () => {
    respondToMe(200)
    renderAt('/app')
    expect(await screen.findByText('Dashboard')).toBeInTheDocument()
  })

  it('skips the sign-in page for a student who is already signed in', async () => {
    respondToMe(200)
    renderAt('/login')
    expect(await screen.findByText('Dashboard')).toBeInTheDocument()
  })
})
