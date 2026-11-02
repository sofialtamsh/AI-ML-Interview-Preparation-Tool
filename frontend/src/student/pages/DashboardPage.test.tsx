import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router'
import { afterEach, describe, expect, it, vi } from 'vitest'

import { ToastProvider } from '../../components/ui/Toast'
import { studentKeys } from '../../lib/queryClient'
import { SUMMARY } from '../../test/fixtures/progress'
import DashboardPage from './DashboardPage'

function renderDashboard() {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  client.setQueryData(studentKeys.me, {
    id: 's1',
    student_code: 'STU-001001',
    full_name: 'Asha Rao',
    email: 'asha@example.com',
    created_at: '2026-10-01T00:00:00Z',
    cohort_name: null,
  })
  render(
    <QueryClientProvider client={client}>
      <ToastProvider>
        <MemoryRouter>
          <DashboardPage />
        </MemoryRouter>
      </ToastProvider>
    </QueryClientProvider>,
  )
}

afterEach(() => vi.unstubAllGlobals())

describe('student dashboard', () => {
  it('shows saved progress: continue, completion, strengths, quizzes and practice', async () => {
    vi.stubGlobal('fetch', vi.fn(async () => Response.json(SUMMARY)))
    renderDashboard()
    expect(await screen.findByText('Pick up where you left off')).toBeInTheDocument()
    expect(screen.getByRole('link', { name: /Continue: Interview/ })).toHaveAttribute('href', '/app/learn/machine-learning/supervised-learning?s=interview')
    expect(screen.getByText('day streak').previousSibling).toHaveTextContent('3')
    expect(screen.getAllByText('67%').length).toBeGreaterThan(0)
    expect(screen.getByText('Boost a weak spot')).toBeInTheDocument()
    expect(screen.getByText('86%')).toBeInTheDocument()
    expect(screen.getByRole('list', { name: 'Recent interview practice scores' })).toBeInTheDocument()
  })
})
