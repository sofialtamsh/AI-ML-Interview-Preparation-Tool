import { describe, expect, it } from 'vitest'

import type { FieldSpec } from '../../../lib/types'
import { initialValues, isVisible, toPayload } from './settingsForm'

const field = (key: string, kind: FieldSpec['kind'], extra: Partial<FieldSpec> = {}): FieldSpec => ({
  key,
  label: key,
  kind,
  help: '',
  placeholder: '',
  options: null,
  required: false,
  default: null,
  min: null,
  max: null,
  visible_when: null,
  ...extra,
})

const FIELDS = [
  field('pagination', 'select', { default: 'none' }),
  field('next_path', 'text', { default: '', visible_when: { pagination: ['next_url', 'cursor'] } }),
  field('link_selector', 'text', { default: '' }),
  field('next_page_selector', 'text', { default: '', visible_when: { link_selector: ['*'] } }),
  field('fetch_full_page', 'checkbox', { default: false }),
  field('content_selector', 'text', { default: '', visible_when: { fetch_full_page: ['true'] } }),
  field('max_pages', 'number', { default: 10 }),
  field('start_urls', 'lines', { default: [] }),
]

const visible = (values: Record<string, unknown>) =>
  FIELDS.filter((f) => isVisible(f, values)).map((f) => f.key)

describe('source settings form', () => {
  it('starts from saved values, falling back to the backend defaults', () => {
    const values = initialValues(FIELDS, { pagination: 'cursor', max_pages: 25 })
    expect(values).toMatchObject({
      pagination: 'cursor',
      max_pages: '25',
      start_urls: [],
      fetch_full_page: false,
    })
  })

  it('shows dependent fields only when they apply', () => {
    const values = initialValues(FIELDS)
    expect(visible(values)).toEqual([
      'pagination',
      'link_selector',
      'fetch_full_page',
      'max_pages',
      'start_urls',
    ])
    expect(
      visible({ ...values, pagination: 'cursor', link_selector: 'a.post', fetch_full_page: true }),
    ).toEqual(FIELDS.map((f) => f.key))
    expect(visible({ ...values, link_selector: '   ' })).not.toContain('next_page_selector')
  })

  it('sends numbers as numbers and lines as a clean list', () => {
    const payload = toPayload(FIELDS, {
      ...initialValues(FIELDS),
      max_pages: '',
      start_urls: ['https://a.example.com/x ', '', '  https://a.example.com/y'],
    })
    expect(payload.max_pages).toBe(10)
    expect(payload.start_urls).toEqual(['https://a.example.com/x', 'https://a.example.com/y'])
    expect(toPayload(FIELDS, { ...initialValues(FIELDS), max_pages: '3.5' }).max_pages).toBe(3.5)
  })
})
