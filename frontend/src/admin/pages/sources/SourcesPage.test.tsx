import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import type { ReactElement } from 'react'
import { createMemoryRouter, RouterProvider } from 'react-router'
import { afterEach, describe, expect, it, vi } from 'vitest'

import { ToastProvider } from '../../../components/ui/Toast'
import { adminKeys } from '../../../lib/queryClient'
import type {
  AdminMe,
  FieldSpec,
  SourceCatalog,
  SourceDetail,
  SourceListItem,
} from '../../../lib/types'
import { CredentialsDialog } from './CredentialsDialog'
import SourcesPage from './SourcesPage'

const ME: AdminMe = {
  id: 'a1',
  email: 'ops@example.com',
  full_name: 'Ops',
  must_change_password: false,
  roles: [],
  permissions: ['sources.view', 'sources.manage', 'sources.credentials.manage'],
}

const secret = (key: string, label: string, kind: FieldSpec['kind']): FieldSpec => ({
  key,
  label,
  kind,
  help: '',
  placeholder: '',
  options: null,
  required: false,
  default: null,
  min: null,
  max: null,
  visible_when: null,
})

const CATALOG: SourceCatalog = {
  connectors: [
    {
      key: 'web_pages',
      label: 'Website pages',
      description: '',
      uses_url: true,
      auth_methods: ['none'],
      settings_fields: [],
    },
    {
      key: 'json_api',
      label: 'JSON API',
      description: '',
      uses_url: true,
      auth_methods: ['none', 'http_basic'],
      settings_fields: [],
    },
  ],
  auth_methods: [
    { key: 'none', label: 'No sign-in', description: '', settings_fields: [], secret_fields: [] },
    {
      key: 'http_basic',
      label: 'Username & password (HTTP Basic)',
      description: '',
      settings_fields: [],
      secret_fields: [
        secret('username', 'Username or email', 'text'),
        secret('password', 'Password', 'password'),
      ],
    },
  ],
  credential_storage_ready: true,
  upload_extensions: ['.csv', '.pdf'],
  max_upload_mb: 10,
}

const source = (overrides: Partial<SourceListItem>): SourceListItem => ({
  id: 's1',
  name: 'Partner portal',
  description: '',
  connector_type: 'web_pages',
  base_url: 'https://interviews.example.com',
  auth_method: 'none',
  enabled: true,
  removed_at: null,
  connection_status: 'ok',
  connection_message: null,
  last_tested_at: null,
  last_attempted_sync_at: null,
  last_successful_sync_at: null,
  record_count: 1204,
  credentials: { required: [], stored: [], complete: true, updated_at: null, updated_by: null },
  active_job: null,
  created_at: '2026-10-27T05:00:00Z',
  ...overrides,
})

const SOURCES = [
  source({}),
  source({
    id: 's2',
    name: 'Careers API',
    connector_type: 'json_api',
    auth_method: 'http_basic',
    connection_status: 'untested',
    record_count: 0,
    credentials: {
      required: ['username', 'password'],
      stored: [],
      complete: false,
      updated_at: null,
      updated_by: null,
    },
  }),
]

function serve(routes: Record<string, unknown>) {
  const fetch = vi.fn(async (url: string, init?: RequestInit) => {
    const path = url.replace(/^\/api/, '').split('?')[0]
    const body = routes[`${init?.method ?? 'GET'} ${path}`]
    if (body === undefined) return new Response('{}', { status: 404 })
    return new Response(JSON.stringify(body), { status: 200 })
  })
  vi.stubGlobal('fetch', fetch)
  return fetch
}

function renderWithProviders(element: ReactElement) {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  client.setQueryData(adminKeys.me, ME)
  const router = createMemoryRouter([{ path: '*', element }])
  render(
    <QueryClientProvider client={client}>
      <ToastProvider>
        <RouterProvider router={router} />
      </ToastProvider>
    </QueryClientProvider>,
  )
}

afterEach(() => vi.unstubAllGlobals())

describe('Interview sources page', () => {
  it('lists sources with their status and what they still need', async () => {
    serve({ 'GET /admin/sources': SOURCES, 'GET /admin/sources/catalog': CATALOG })
    renderWithProviders(<SourcesPage />)
    expect(await screen.findByText('Partner portal')).toBeInTheDocument()
    expect(screen.getByText('Connected')).toBeInTheDocument()
    expect(screen.getByText('Needs credentials')).toBeInTheDocument()
    expect(screen.getByText(/Website pages · interviews.example.com/)).toBeInTheDocument()
    expect(screen.getByText('1.2K')).toBeInTheDocument()
  })

  it('fetches the selected sources together', async () => {
    const fetch = serve({
      'GET /admin/sources': SOURCES,
      'GET /admin/sources/catalog': CATALOG,
      'POST /admin/sources/fetch': { started: [], skipped: [] },
    })
    renderWithProviders(<SourcesPage />)
    fireEvent.click(await screen.findByLabelText('Select Partner portal'))
    fireEvent.click(screen.getByRole('button', { name: /Fetch 1/ }))
    await waitFor(() =>
      expect(fetch).toHaveBeenCalledWith(
        '/api/admin/sources/fetch',
        expect.objectContaining({ method: 'POST' }),
      ),
    )
    const [, init] = fetch.mock.calls.find(([url]) => url === '/api/admin/sources/fetch')!
    expect(JSON.parse(init!.body as string)).toEqual({ source_ids: ['s1'] })
  })
})

describe('credentials dialog', () => {
  it('never shows stored values and only sends what was typed', async () => {
    const detail: SourceDetail = {
      ...SOURCES[1],
      credentials: { ...SOURCES[1].credentials, stored: ['password', 'username'], complete: true },
      config: {},
      auth_config: {},
    }
    const fetch = serve({ 'PUT /admin/sources/s2/credentials': detail })
    renderWithProviders(
      <CredentialsDialog catalog={CATALOG} source={detail} onClose={() => {}} />,
    )

    const username = screen.getByLabelText('Username or email') as HTMLInputElement
    const password = screen.getByLabelText('Password') as HTMLInputElement
    expect(username.value).toBe('')
    expect(password.placeholder).toBe('Saved · leave blank to keep')
    expect(password.type).toBe('password')

    fireEvent.change(password, { target: { value: 'n3w-pass' } })
    fireEvent.click(screen.getByRole('button', { name: 'Save credentials', hidden: true }))
    await waitFor(() => expect(fetch).toHaveBeenCalled())
    const [url, init] = fetch.mock.calls[0]
    expect(url).toBe('/api/admin/sources/s2/credentials')
    expect(JSON.parse(init!.body as string)).toEqual({
      values: { username: '', password: 'n3w-pass' },
    })
  })
})
