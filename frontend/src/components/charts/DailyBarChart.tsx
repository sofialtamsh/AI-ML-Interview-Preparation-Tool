import type { DailyCount } from '../../lib/types'
import { BarChart } from './BarChart'

export { integerTicks } from './BarChart'

const dayLabel = new Intl.DateTimeFormat(undefined, { day: 'numeric', month: 'short' })
const longDayLabel = new Intl.DateTimeFormat(undefined, {
  weekday: 'short',
  day: 'numeric',
  month: 'short',
})
const parseDay = (day: string) => new Date(`${day}T00:00:00`)

/** Daily student registrations. */
export function DailyBarChart({ data, label }: { data: DailyCount[]; label: string }) {
  return (
    <BarChart
      data={data.map((d) => ({
        key: d.day,
        label: dayLabel.format(parseDay(d.day)),
        long: longDayLabel.format(parseDay(d.day)),
        value: d.count,
      }))}
      label={label}
      unit={['registration', 'registrations']}
      column="Day"
    />
  )
}
