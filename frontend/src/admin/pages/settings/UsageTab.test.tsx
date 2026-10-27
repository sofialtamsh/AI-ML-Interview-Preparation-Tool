import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { fireEvent, render, screen, within } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'

import type { AiProviderStatus, AiUsageReport } from '../../../lib/types'
import UsageTab, { humanize } from './UsageTab'

const week = (start: string, end: string, calls: number, cost: string) => ({
  start,
  end,
  calls,
  input_tokens: calls * 1000,
  output_tokens: calls * 100,
  cost_usd: cost,
})

const REPORT: AiUsageReport = {
  currency: 'USD',
  tracking_start: '2026-10-27',
  timezone: 'Asia/Kolkata',
  weeks: [
    week('2026-11-03', '2026-11-09', 3, '0.45'),
    week('2026-10-27', '2026-11-02', 2, '1.75'),
  ],
  selected: {
    start: '2026-11-03',
    end: '2026-11-09',
    by_feature: [{ key: 'content_generation', calls: 3, cost_usd: '0.45' }],
    by_model: [{ key: 'openai/gpt-test', calls: 3, cost_usd: '0.45' }],
  },
  all_time: { calls: 5, input_tokens: 5000, output_tokens: 500, cost_usd: '2.2' },
}

const NOT_CONFIGURED: AiProviderStatus = {
  provider: 'openrouter',
  configured: false,
  ok: false,
  error: null,
  key_usage_usd: null,
  cap: null,
  is_free_tier: null,
}

function serve(report: AiUsageReport, provider: AiProviderStatus = NOT_CONFIGURED) {
  const fetch = vi.fn(async (url: string) => {
    const body = url.includes('/provider') ? provider : report
    return new Response(JSON.stringify(body), { status: 200 })
  })
  vi.stubGlobal('fetch', fetch)
  return fetch
}

function renderTab() {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  render(
    <QueryClientProvider client={client}>
      <UsageTab />
    </QueryClientProvider>,
  )
}

afterEach(() => vi.unstubAllGlobals())

describe('AI usage tab', () => {
  it('shows this week, last week and the running total', async () => {
    serve(REPORT)
    renderTab()
    expect(await screen.findByText('$0.45', { selector: 'p' })).toBeInTheDocument()
    expect(screen.getByText('$1.75', { selector: 'p' })).toBeInTheDocument()
    expect(screen.getByText('$2.20', { selector: 'p' })).toBeInTheDocument()
    expect(screen.getByText(/Weeks run Tuesday to Monday/)).toBeInTheDocument()
    expect(screen.getByText('Content generation')).toBeInTheDocument()
    expect(await screen.findByText('Not connected')).toBeInTheDocument()
  })

  it('loads the breakdown of an earlier week when it is selected', async () => {
    const fetch = serve(REPORT)
    renderTab()
    const table = await screen.findByRole('table')
    const rows = within(table).getAllByRole('button')
    expect(rows[0]).toHaveAttribute('aria-pressed', 'true')
    fireEvent.click(rows[1])
    await vi.waitFor(() =>
      expect(fetch).toHaveBeenCalledWith('/api/admin/ai-usage?week=2026-10-27', expect.anything()),
    )
  })

  it('shows the key status reported by the API without any secret', async () => {
    serve(REPORT, {
      ...NOT_CONFIGURED,
      configured: true,
      ok: true,
      key_usage_usd: '3.21',
      cap: { limit_usd: '20', remaining_usd: '14.5', reset_interval: 'weekly', resets_at: null },
    })
    renderTab()
    expect(await screen.findByText('Connected')).toBeInTheDocument()
    expect(screen.getByText('$3.21')).toBeInTheDocument()
    expect(screen.getByText('$14.50')).toBeInTheDocument()
    expect(screen.getByText('a week')).toBeInTheDocument()
  })

  it('humanizes feature keys', () => {
    expect(humanize('exploration_agent')).toBe('Exploration agent')
  })
})
