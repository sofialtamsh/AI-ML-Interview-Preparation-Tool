const dateFormat = new Intl.DateTimeFormat(undefined, {
  day: 'numeric',
  month: 'short',
  year: 'numeric',
})
const dateTimeFormat = new Intl.DateTimeFormat(undefined, {
  day: 'numeric',
  month: 'short',
  year: 'numeric',
  hour: 'numeric',
  minute: '2-digit',
})
const numberFormat = new Intl.NumberFormat(undefined, { notation: 'compact' })

export const formatDate = (iso: string | null | undefined) =>
  iso ? dateFormat.format(new Date(iso)) : '—'

export const formatDateTime = (iso: string | null | undefined) =>
  iso ? dateTimeFormat.format(new Date(iso)) : '—'

export const formatCount = (value: number) => numberFormat.format(value)

export function timeAgo(iso: string | null | undefined, now = Date.now()): string {
  if (!iso) return 'Never'
  const seconds = Math.round((now - new Date(iso).getTime()) / 1000)
  if (seconds < 60) return 'Just now'
  const minutes = Math.round(seconds / 60)
  if (minutes < 60) return `${minutes} min ago`
  const hours = Math.round(minutes / 60)
  if (hours < 24) return `${hours} h ago`
  const days = Math.round(hours / 24)
  if (days < 7) return `${days} day${days === 1 ? '' : 's'} ago`
  return formatDate(iso)
}

export function initials(name: string): string {
  const parts = name.trim().split(/\s+/).filter(Boolean)
  const letters = parts.length > 1 ? [parts[0][0], parts.at(-1)![0]] : [parts[0]?.[0] ?? '?']
  return letters.join('').toUpperCase()
}

/** "Chrome on Windows"-style label for a session's user agent. */
export function describeDevice(userAgent: string | null): string {
  if (!userAgent) return 'Unknown device'
  const browser =
    /Edg\//.test(userAgent) ? 'Edge'
    : /OPR\//.test(userAgent) ? 'Opera'
    : /Firefox\//.test(userAgent) ? 'Firefox'
    : /Chrome\//.test(userAgent) ? 'Chrome'
    : /Safari\//.test(userAgent) ? 'Safari'
    : 'Browser'
  const os =
    /Windows/.test(userAgent) ? 'Windows'
    : /Android/.test(userAgent) ? 'Android'
    : /iPhone|iPad|iPod/.test(userAgent) ? 'iOS'
    : /Mac OS X/.test(userAgent) ? 'macOS'
    : /Linux/.test(userAgent) ? 'Linux'
    : null
  return os ? `${browser} on ${os}` : browser
}

export const isMobileDevice = (userAgent: string | null) =>
  !!userAgent && /Android|iPhone|iPad|iPod|Mobile/.test(userAgent)

const usd = new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD' })
const usdSmall = new Intl.NumberFormat('en-US', {
  style: 'currency',
  currency: 'USD',
  maximumFractionDigits: 4,
})

/** "$12.40"; amounts under a cent keep four decimals ("$0.0042") so small calls never read as $0. */
export function formatUsd(value: string | number): string {
  const amount = Number(value)
  return amount !== 0 && Math.abs(amount) < 0.01 ? usdSmall.format(amount) : usd.format(amount)
}

// Date-only API values ("2026-10-27") are calendar days, so format them in UTC to avoid shifting.
const dayRange = new Intl.DateTimeFormat(undefined, {
  day: 'numeric',
  month: 'short',
  year: 'numeric',
  timeZone: 'UTC',
})
const weekday = new Intl.DateTimeFormat(undefined, { weekday: 'long', timeZone: 'UTC' })

export const formatDayRange = (start: string, end: string) =>
  dayRange.formatRange(new Date(start), new Date(end))

export const formatDay = (day: string) => dayRange.format(new Date(day))

export const formatWeekday = (day: string) => weekday.format(new Date(day))
