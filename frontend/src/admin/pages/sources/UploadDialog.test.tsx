import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'

import type { JobSummary, SourceCatalog, SourceDetail } from '../../../lib/types'
import { describeFileTypes, UploadDialog } from './UploadDialog'

const CATALOG = {
  connectors: [],
  auth_methods: [],
  credential_storage_ready: true,
  upload_extensions: ['.csv', '.pdf'],
  max_upload_mb: 10,
} satisfies SourceCatalog

const SOURCE = { id: 's1', name: 'Alumni notes', enabled: true } as SourceDetail

const JOB: Partial<JobSummary> = {
  id: 'j1',
  kind: 'source_import',
  status: 'succeeded',
  result: { new: 3, unchanged: 1 },
}

afterEach(() => vi.unstubAllGlobals())

describe('file import dialog', () => {
  it('names the accepted file types in plain words', () => {
    expect(
      describeFileTypes(['.csv', '.docx', '.htm', '.html', '.json', '.jsonl', '.md', '.pdf', '.txt']),
    ).toBe('CSV, Word (.docx), saved web pages, JSON, Markdown, PDF or text')
  })

  it('keeps the chosen files and uploads each with the column options', async () => {
    const fetch = vi.fn(async () => new Response(JSON.stringify(JOB), { status: 201 }))
    vi.stubGlobal('fetch', fetch)
    const client = new QueryClient()
    render(
      <QueryClientProvider client={client}>
        <UploadDialog catalog={CATALOG} source={SOURCE} onClose={() => {}} />
      </QueryClientProvider>,
    )

    const input = screen.getByLabelText('Files to import') as HTMLInputElement
    const csv = new File(['id,question\n1,What is dropout?\n'], 'questions.csv', { type: 'text/csv' })
    // Like a browser's live FileList, clearing the input's value empties `files`. The dialog
    // clears it right after a pick, so it must copy the files first.
    const live: File[] = [csv]
    Object.defineProperty(input, 'files', { configurable: true, get: () => live })
    Object.defineProperty(input, 'value', {
      configurable: true,
      get: () => (live.length ? 'C:\\fakepath\\questions.csv' : ''),
      set: (value: string) => {
        if (value === '') live.length = 0
      },
    })
    fireEvent.change(input)

    expect(await screen.findByText('questions.csv')).toBeInTheDocument()
    fireEvent.change(screen.getByLabelText('ID column (optional)'), { target: { value: 'id' } })
    fireEvent.click(screen.getByRole('button', { name: 'Import file', hidden: true }))

    expect(await screen.findByText('3 new · 1 unchanged')).toBeInTheDocument()
    await waitFor(() => expect(fetch).toHaveBeenCalledTimes(1))
    const [url, init] = fetch.mock.calls[0] as unknown as [string, RequestInit]
    expect(url).toBe('/api/admin/sources/s1/upload')
    const form = init.body as FormData
    expect((form.get('file') as File).name).toBe('questions.csv')
    expect(form.get('id_field')).toBe('id')
    expect(init.headers).not.toHaveProperty('Content-Type') // the browser sets the multipart boundary
  })
})
