/** Thin fetch wrapper for the platform API (same origin, cookie sessions). */

export type Audience = 'admin' | 'student'

export class ApiError extends Error {
  readonly status: number
  readonly fieldErrors: Record<string, string>

  constructor(status: number, message: string, fieldErrors: Record<string, string> = {}) {
    super(message)
    this.name = 'ApiError'
    this.status = status
    this.fieldErrors = fieldErrors
  }
}

type ValidationIssue = { loc?: (string | number)[]; msg?: string }

let onUnauthorized: (audience: Audience) => void = () => {}

/** Called when an authenticated request finds its session gone (expired, revoked, suspended). */
export function setUnauthorizedHandler(handler: (audience: Audience) => void): void {
  onUnauthorized = handler
}

function humanise(field: string): string {
  const label = field.replace(/_/g, ' ')
  return label.charAt(0).toUpperCase() + label.slice(1)
}

function parseError(status: number, body: unknown): ApiError {
  const detail = (body as { detail?: unknown } | null)?.detail
  if (typeof detail === 'string') return new ApiError(status, detail)
  if (Array.isArray(detail)) {
    const fieldErrors: Record<string, string> = {}
    for (const issue of detail as ValidationIssue[]) {
      const field = String(issue.loc?.at(-1) ?? 'request')
      const message = (issue.msg ?? 'Invalid value').replace(/^Value error, /, '')
      fieldErrors[field] ??= message
    }
    const summary = Object.entries(fieldErrors)
      .map(([field, message]) => `${humanise(field)}: ${message}`)
      .join(' ')
    return new ApiError(status, summary || 'Please check the form and try again.', fieldErrors)
  }
  if (status === 429) return new ApiError(status, 'Too many requests. Please wait a moment.')
  if (status >= 500) return new ApiError(status, 'Something went wrong on our side. Please try again.')
  return new ApiError(status, 'Request failed. Please try again.')
}

const SESSION_PROBES = ['/auth/login', '/auth/me', '/auth/register', '/auth/logout']

export async function api<T>(
  path: string,
  options: { method?: string; body?: unknown; signal?: AbortSignal } = {},
): Promise<T> {
  let response: Response
  try {
    response = await fetch(`/api${path}`, {
      method: options.method ?? 'GET',
      credentials: 'same-origin',
      headers: {
        // Required by the API on state-changing requests (CSRF defence).
        'X-Requested-With': 'ipp-web',
        ...(options.body !== undefined ? { 'Content-Type': 'application/json' } : {}),
      },
      body: options.body !== undefined ? JSON.stringify(options.body) : undefined,
      signal: options.signal,
    })
  } catch (error) {
    if ((error as Error).name === 'AbortError') throw error
    throw new ApiError(0, 'Cannot reach the server. Check your connection and try again.')
  }

  if (response.status === 204) return undefined as T
  const body: unknown = await response.json().catch(() => null)
  if (response.ok) return body as T

  const audience: Audience | null = path.startsWith('/admin/')
    ? 'admin'
    : path.startsWith('/student/')
      ? 'student'
      : null
  if (response.status === 401 && audience && !SESSION_PROBES.some((p) => path.endsWith(p))) {
    onUnauthorized(audience)
  }
  throw parseError(response.status, body)
}

export function errorMessage(error: unknown): string {
  if (error instanceof ApiError) return error.message
  return 'Something went wrong. Please try again.'
}
