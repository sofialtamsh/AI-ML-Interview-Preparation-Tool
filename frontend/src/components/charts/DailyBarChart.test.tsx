import { fireEvent, render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'

import { DailyBarChart } from './DailyBarChart'

const DATA = [
  { day: '2026-10-25', count: 2 },
  { day: '2026-10-26', count: 0 },
  { day: '2026-10-27', count: 5 },
]

describe('DailyBarChart', () => {
  it('offers every value in a table view', () => {
    render(<DailyBarChart data={DATA} label="Registrations" />)
    const rows = screen.getAllByRole('row')
    expect(rows).toHaveLength(DATA.length + 1)
    expect(rows.at(-1)).toHaveTextContent('5')
  })

  it('reads days aloud with the keyboard', () => {
    render(<DailyBarChart data={DATA} label="Registrations" />)
    const chart = screen.getByRole('group', { name: /Registrations/ })
    fireEvent.keyDown(chart, { key: 'ArrowLeft' })
    expect(screen.getByRole('status')).toHaveTextContent('5 registrations')
    fireEvent.keyDown(chart, { key: 'ArrowLeft' })
    expect(screen.getByRole('status')).toHaveTextContent('0 registrations')
    fireEvent.keyDown(chart, { key: 'Escape' })
    expect(screen.queryByRole('status')).not.toBeInTheDocument()
  })
})
