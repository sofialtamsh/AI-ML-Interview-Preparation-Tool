import { afterEach, describe, expect, it, vi } from 'vitest'

import { api, ApiError, setUnauthorizedHandler } from './api'

function mockFetch(status: number, body?: unknown) {
  const fetchMock = vi.fn().mockResolvedValue(
    new Response(body === undefined ? null : JSON.stringify(body), {
      status,
      headers: { 'Content-Type': 'application/json' },
    }),
  )
  vi.stubGlobal('fetch', fetchMock)
  return fetchMock
}

afterEach(() => {
  vi.unstubAllGlobals()
  setUnauthorizedHandler(() => {})
})

describe('api', () => {
  it('sends the CSRF header and a JSON body to the same-origin API', async () => {
    const fetchMock = mockFetch(200, { ok: true })
    await api('/student/auth/login', { method: 'POST', body: { email: 'a@b.co' } })

    const [url, init] = fetchMock.mock.calls[0]
    expect(url).toBe('/api/student/auth/login')
    expect(init.credentials).toBe('same-origin')
    expect(init.headers['X-Requested-With']).toBe('ipp-web')
    expect(init.headers['Content-Type']).toBe('application/json')
    expect(init.body).toBe('{"email":"a@b.co"}')
  })

  it('returns undefined for 204 responses', async () => {
    mockFetch(204)
    await expect(api('/student/auth/logout', { method: 'POST' })).resolves.toBeUndefined()
  })

  it('surfaces the server message for errors', async () => {
    mockFetch(409, { detail: 'An account with this email already exists.' })
    await expect(api('/student/auth/register')).rejects.toMatchObject({
      status: 409,
      message: 'An account with this email already exists.',
    })
  })

  it('turns validation errors into per-field messages', async () => {
    mockFetch(422, {
      detail: [
        { loc: ['body', 'password'], msg: 'String should have at least 10 characters' },
        { loc: ['body', 'email'], msg: 'value is not a valid email address' },
      ],
    })
    const error = (await api('/student/auth/register').catch((e) => e)) as ApiError
    expect(error).toBeInstanceOf(ApiError)
    expect(error.fieldErrors).toEqual({
      password: 'String should have at least 10 characters',
      email: 'value is not a valid email address',
    })
    expect(error.message).toContain('Password: String should have at least 10 characters')
  })

  it('reports an ended session for authenticated calls only', async () => {
    const handler = vi.fn()
    setUnauthorizedHandler(handler)

    mockFetch(401, { detail: 'Not authenticated.' })
    await api('/admin/students').catch(() => {})
    expect(handler).toHaveBeenCalledWith('admin')

    handler.mockClear()
    mockFetch(401, { detail: 'Invalid email or password.' })
    await api('/student/auth/login', { method: 'POST', body: {} }).catch(() => {})
    expect(handler).not.toHaveBeenCalled()
  })

  it('explains network failures', async () => {
    vi.stubGlobal('fetch', vi.fn().mockRejectedValue(new TypeError('Failed to fetch')))
    await expect(api('/student/auth/me')).rejects.toMatchObject({ status: 0 })
  })
})
