import { describe, expect, it } from 'vitest'

import { describeDetails } from '../admin/pages/settings/AuditTab'
import { integerTicks } from '../components/charts/DailyBarChart'
import { describeDevice, formatDayRange, formatUsd, initials, timeAgo } from './format'
import { generateTemporaryPassword, scorePassword } from './password'

describe('scorePassword', () => {
  it('rejects short passwords and rewards length and variety', () => {
    expect(scorePassword('short').score).toBe(0)
    expect(scorePassword('aaaaaaaaaaaa').score).toBe(1)
    expect(scorePassword('longerpassword').score).toBe(2)
    expect(scorePassword('Longer-Passw0rd!').score).toBe(3)
    expect(scorePassword('A much Longer passphrase 42!').score).toBe(4)
  })
})

describe('generateTemporaryPassword', () => {
  it('produces unambiguous passwords of the requested length', () => {
    const password = generateTemporaryPassword(20)
    expect(password).toHaveLength(20)
    expect(password).not.toMatch(/[0O1lI]/)
    expect(generateTemporaryPassword()).not.toBe(generateTemporaryPassword())
  })
})

describe('format helpers', () => {
  it('describes devices from user agents', () => {
    const chromeWindows =
      'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/140.0 Safari/537.36'
    const safariIphone =
      'Mozilla/5.0 (iPhone; CPU iPhone OS 18_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.0 Mobile/15E148 Safari/604.1'
    expect(describeDevice(chromeWindows)).toBe('Chrome on Windows')
    expect(describeDevice(safariIphone)).toBe('Safari on iOS')
    expect(describeDevice(null)).toBe('Unknown device')
  })

  it('renders relative times', () => {
    const now = Date.parse('2026-10-27T12:00:00Z')
    expect(timeAgo('2026-10-27T11:59:30Z', now)).toBe('Just now')
    expect(timeAgo('2026-10-27T11:15:00Z', now)).toBe('45 min ago')
    expect(timeAgo('2026-10-25T12:00:00Z', now)).toBe('2 days ago')
    expect(timeAgo(null, now)).toBe('Never')
  })

  it('builds initials', () => {
    expect(initials('Asha Rao')).toBe('AR')
    expect(initials('  meera  ')).toBe('M')
  })
})

describe('integerTicks', () => {
  it('keeps a readable minimum scale and clean steps', () => {
    expect(integerTicks(0)).toEqual([0, 1, 2, 3, 4])
    expect(integerTicks(3)).toEqual([0, 1, 2, 3, 4])
    expect(integerTicks(9)).toEqual([0, 5, 10])
    expect(integerTicks(37)).toEqual([0, 10, 20, 30, 40])
  })
})

describe('describeDetails', () => {
  it('renders audit changes readably', () => {
    expect(
      describeDetails({
        status: { from: 'active', to: 'suspended' },
        cohort_id: { from: null, to: 'abc' },
        roles: ['analyst'],
      }),
    ).toEqual(['status: active → suspended', 'cohort id: — → abc', 'roles: analyst'])
  })
})

describe('formatUsd', () => {
  it('shows cents, keeping sub-cent amounts visible', () => {
    expect(formatUsd('12.4')).toBe('$12.40')
    expect(formatUsd('1234.5')).toBe('$1,234.50')
    expect(formatUsd('0')).toBe('$0.00')
    expect(formatUsd('0.00042')).toBe('$0.0004')
    expect(formatUsd('0.0042')).toBe('$0.0042')
  })
})

describe('formatDayRange', () => {
  it('treats API dates as calendar days in every timezone', () => {
    const text = formatDayRange('2026-10-27', '2026-11-02')
    expect(text).toMatch(/27/)
    expect(text).toMatch(/2026/)
    expect(text).not.toMatch(/\b26\b/)
  })
})
