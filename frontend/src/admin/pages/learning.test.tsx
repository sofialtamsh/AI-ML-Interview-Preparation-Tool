import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import type { ReactNode } from 'react'
import { MemoryRouter } from 'react-router'
import { afterEach, describe, expect, it, vi } from 'vitest'

import { LEARNING, REPORT } from '../../test/fixtures/progress'
import AnalyticsPage from './AnalyticsPage'
import { StudentLearningPanel } from './StudentLearningPanel'

const ASHA = { id: 's1', full_name: 'Asha Rao', student_code: 'STU-0001' }

function serve(permissions: string[]) {
  const fetch = vi.fn(async (url: string) => {
    if (url.endsWith('/auth/me')) return Response.json({ id: 'a', email: 'a@x.com', full_name: 'A', permissions })
    if (url.includes('/learning')) return Response.json(LEARNING)
    if (url.includes('/admin/analytics')) return Response.json(url.includes('student_id=s1') ? { ...REPORT, student: ASHA, cohorts: [] } : REPORT)
    if (url.includes('/admin/students?')) {
      const items = [{ ...ASHA, email: 'asha@example.com', status: 'active', created_at: '2026-10-01T00:00:00Z', last_login_at: null }]
      return Response.json({ items, total: 1, page: 1, page_size: 8 })
    }
    return Response.json({ detail: 'Not found' }, { status: 404 })
  })
  vi.stubGlobal('fetch', fetch)
  return fetch
}

function wrap(children: ReactNode, path = '/') {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return render(
    <QueryClientProvider client={client}>
      <MemoryRouter initialEntries={[path]}>{children}</MemoryRouter>
    </QueryClientProvider>,
  )
}

afterEach(() => vi.unstubAllGlobals())

describe('student learning panel', () => {
  it('shows progress, mastery and history without transcripts', async () => {
    serve(['students.view'])
    wrap(<StudentLearningPanel studentId="s1" />)
    expect(await screen.findByText('67%')).toBeInTheDocument()
    expect(screen.getByText('Strong 💪')).toBeInTheDocument()
    expect(screen.getByText('Needs work')).toBeInTheDocument()
    expect(screen.getByText(/Scores only; recordings never reach the server/)).toBeInTheDocument()
    expect(screen.getByText('Almost there')).toBeInTheDocument()
    // Time spent learning: 2100 s in all, 900 s this week, and per topic.
    expect(screen.getByText('35 min')).toBeInTheDocument()
    expect(screen.getByText('15 min in the last 7 days')).toBeInTheDocument()
    expect(screen.getByText('25 min')).toBeInTheDocument()
  })

  it('compares two attempts of the same quiz question by question', async () => {
    serve(['students.view'])
    wrap(<StudentLearningPanel studentId="s1" />)
    await userEvent.click(await screen.findByLabelText('Compare Supervised Learning attempt 2'))
    await userEvent.click(screen.getByLabelText('Compare Supervised Learning attempt 1'))
    const table = screen.getByRole('table', { name: 'Attempt comparison' })
    expect(within(table).getByText('Attempt 1 (50%)')).toBeInTheDocument()
    expect(within(table).getByText('Attempt 2 (100%)')).toBeInTheDocument()
    const first = within(table).getByText('Question 1?').closest('tr')!
    expect(within(first).getByLabelText('Wrong')).toBeInTheDocument()
    expect(within(first).getByLabelText('Correct')).toBeInTheDocument()

    await userEvent.click(screen.getByLabelText('Compare Supervised Learning attempt 1'))
    await userEvent.click(screen.getByLabelText('Compare Regression attempt 1'))
    expect(screen.getByText(/Pick two attempts of the same topic/)).toBeInTheDocument()
  })
})

describe('analytics page', () => {
  it('shows KPIs, charts, weak topics and cohorts, with export for permitted admins', async () => {
    const fetch = serve(['analytics.view', 'analytics.export'])
    wrap(<AnalyticsPage />, '/admin/analytics')
    expect(await screen.findByText('Need attention')).toBeInTheDocument()
    expect(screen.getByRole('link', { name: /See who/ })).toHaveAttribute('href', '/admin/students?attention=any')
    expect(screen.getByRole('link', { name: /Export students/ })).toHaveAttribute('href', '/api/admin/analytics/students.csv')
    expect(screen.getByRole('group', { name: /Quiz attempts by score/ })).toBeInTheDocument()
    expect(screen.getAllByText('Regression').length).toBeGreaterThan(0)
    expect(screen.getByText('Batch A', { selector: 'td' })).toBeInTheDocument()
    expect(screen.getByText('31%')).toBeInTheDocument() // average path completion
    expect(screen.getByText('12 h 30 min')).toBeInTheDocument() // learning time
    expect(screen.getByText('30 min per learner')).toBeInTheDocument()
    expect(screen.getAllByText('3 h 30 min').length).toBeGreaterThan(0) // per topic

    await userEvent.selectOptions(screen.getByLabelText('Topic'), 'machine-learning/regression')
    await vi.waitFor(() => expect(fetch).toHaveBeenCalledWith(expect.stringContaining('topic=machine-learning%2Fregression'), expect.anything()))
  })

  it('hides the export and the student filter from admins without those permissions', async () => {
    serve(['analytics.view'])
    wrap(<AnalyticsPage />, '/admin/analytics?student_id=s1')
    await screen.findByText('Need attention')
    expect(screen.queryByRole('link', { name: /Export students/ })).not.toBeInTheDocument()
    expect(screen.queryByRole('combobox', { name: 'Student' })).not.toBeInTheDocument()
    expect(screen.queryByText(/Showing only/)).not.toBeInTheDocument()
  })

  it('filters to one student picked from a search', async () => {
    const fetch = serve(['analytics.view', 'students.view'])
    wrap(<AnalyticsPage />, '/admin/analytics')
    await screen.findByText('Need attention')
    await userEvent.type(screen.getByRole('combobox', { name: 'Student' }), 'Asha')
    await vi.waitFor(() => expect(fetch).toHaveBeenCalledWith(expect.stringContaining('q=Asha'), expect.anything()))
    await userEvent.click(await screen.findByRole('option', { name: /Asha Rao/ }))

    await vi.waitFor(() => expect(fetch).toHaveBeenCalledWith(expect.stringContaining('student_id=s1'), expect.anything()))
    expect(await screen.findByText(/Showing only Asha Rao/)).toBeInTheDocument()
    expect(screen.getByRole('link', { name: 'Open their profile' })).toHaveAttribute('href', '/admin/students/s1')
    expect(await screen.findByText(/Cohorts aren.t compared/)).toBeInTheDocument()

    await userEvent.click(screen.getByRole('button', { name: 'Show all students' }))
    expect(screen.queryByText(/Showing only/)).not.toBeInTheDocument()
    expect(screen.getByRole('combobox', { name: 'Student' })).toBeInTheDocument()
  })

  it('names the student after a reload, from the report', async () => {
    serve(['analytics.view', 'students.view'])
    wrap(<AnalyticsPage />, '/admin/analytics?student_id=s1')
    expect(await screen.findByText(/Showing only Asha Rao/)).toBeInTheDocument()
    expect(screen.getByText('STU-0001')).toBeInTheDocument()
  })
})
