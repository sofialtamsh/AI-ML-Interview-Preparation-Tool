import { CalendarClock, CircleDollarSign, RefreshCw } from 'lucide-react'
import { useState } from 'react'

import { Button } from '../../../components/ui/Button'
import { Alert, Badge, Card, CardHeader, EmptyState, Skeleton } from '../../../components/ui/Feedback'
import { errorMessage } from '../../../lib/api'
import { cn } from '../../../lib/cn'
import {
  formatCount,
  formatDate,
  formatDay,
  formatDayRange,
  formatUsd,
  formatWeekday,
} from '../../../lib/format'
import type { AiProviderStatus, AiUsageReport, UsageSlice } from '../../../lib/types'
import { useAiProviderStatus, useAiUsage } from '../../api'

/** "content_generation" → "Content generation" */
export function humanize(key: string): string {
  const words = key.replace(/[_-]+/g, ' ').trim()
  return words.charAt(0).toUpperCase() + words.slice(1)
}

/** "Asia/Kolkata" → "India Standard Time" where the browser knows the zone's name. */
function zoneName(timeZone: string): string {
  try {
    const parts = new Intl.DateTimeFormat('en-US', { timeZone, timeZoneName: 'long' }).formatToParts()
    return parts.find((p) => p.type === 'timeZoneName')?.value ?? timeZone
  } catch {
    return timeZone
  }
}

const addDays = (day: string, days: number) =>
  new Date(Date.parse(day) + days * 86_400_000).toISOString().slice(0, 10)

const plural = (count: number, word: string) => `${formatCount(count)} ${word}${count === 1 ? '' : 's'}`

const CAP_PERIOD: Record<string, string> = { daily: 'a day', weekly: 'a week', monthly: 'a month' }

function StatTile({ label, value, note }: { label: string; value: string; note: string }) {
  return (
    <Card className="p-5">
      <p className="text-sm font-medium text-slate-500">{label}</p>
      <p className="mt-2 font-sans text-3xl font-semibold tracking-tight text-slate-900 tabular-nums">
        {value}
      </p>
      <p className="mt-1 text-xs text-slate-500">{note}</p>
    </Card>
  )
}

function ProviderDetails({ data }: { data: AiProviderStatus }) {
  if (!data.configured) {
    return (
      <p className="text-sm text-slate-600">
        No API key is configured. Set{' '}
        <code className="rounded bg-slate-100 px-1.5 py-0.5 text-xs">IPP_OPENROUTER_API_KEY</code> in
        the API&apos;s environment (<code className="text-xs">backend/.env</code> on a dev machine, the
        host&apos;s secret settings in production) and restart the API. The key itself is never shown
        here.
      </p>
    )
  }
  if (!data.ok) return <Alert>{data.error}</Alert>

  const { cap } = data
  const period = cap?.reset_interval ? CAP_PERIOD[cap.reset_interval] : undefined
  return (
    <>
      <dl className="grid grid-cols-1 gap-4 sm:grid-cols-3">
        <div>
          <dt className="text-xs font-medium text-slate-500">Spent on this key, all time</dt>
          <dd className="mt-1 text-xl font-semibold text-slate-900 tabular-nums">
            {formatUsd(data.key_usage_usd ?? 0)}
          </dd>
        </div>
        <div>
          <dt className="text-xs font-medium text-slate-500">Spending cap</dt>
          <dd className="mt-1 text-xl font-semibold text-slate-900 tabular-nums">
            {cap ? (
              <>
                {formatUsd(cap.limit_usd)}
                {period && <span className="text-sm font-normal text-slate-500"> {period}</span>}
              </>
            ) : (
              <span className="text-base font-medium text-slate-500">None set</span>
            )}
          </dd>
        </div>
        <div>
          <dt className="text-xs font-medium text-slate-500">Left under the cap</dt>
          <dd className="mt-1 text-xl font-semibold text-slate-900 tabular-nums">
            {cap?.remaining_usd != null ? formatUsd(cap.remaining_usd) : '—'}
            {cap?.resets_at && (
              <span className="block text-xs font-normal text-slate-500">
                Resets {formatDate(cap.resets_at)}
              </span>
            )}
          </dd>
        </div>
      </dl>
      <p className="mt-4 text-xs text-slate-500">
        OpenRouter&apos;s totals include any use of this key outside the platform.
        {!cap && ' Set a weekly budget on the key in OpenRouter to get a hard spending limit.'}
      </p>
    </>
  )
}

function ProviderCard() {
  const status = useAiProviderStatus()
  const data = status.data

  const badge =
    !data ? null
    : !data.configured ? <Badge>Not connected</Badge>
    : data.ok ? <Badge tone="success">Connected</Badge>
    : <Badge tone="danger">Connection failed</Badge>

  return (
    <Card>
      <CardHeader
        title="OpenRouter key"
        description="Live figures from OpenRouter. Checking them costs nothing."
        action={
          <div className="flex items-center gap-2">
            {badge}
            <Button
              variant="secondary"
              size="sm"
              onClick={() => status.refetch()}
              disabled={status.isFetching}
              icon={<RefreshCw aria-hidden className={cn('size-4', status.isFetching && 'animate-spin')} />}
            >
              Refresh
            </Button>
          </div>
        }
      />
      <div className="p-5">
        {status.isPending ? (
          <Skeleton className="h-16" />
        ) : status.isError ? (
          <Alert>{errorMessage(status.error)}</Alert>
        ) : (
          <ProviderDetails data={status.data} />
        )}
      </div>
    </Card>
  )
}

function WeeksTable({
  report,
  onSelect,
}: {
  report: AiUsageReport
  onSelect: (start: string) => void
}) {
  const max = Math.max(0, ...report.weeks.map((w) => Number(w.cost_usd)))
  return (
    <Card className="overflow-hidden">
      <CardHeader
        title="Weekly spend"
        description="Newest first. Select a week to see where the money went."
      />
      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead className="bg-slate-50 text-left text-xs font-medium text-slate-500">
            <tr>
              <th scope="col" className="px-5 py-2.5">Week</th>
              <th scope="col" className="px-3 py-2.5 text-right">Calls</th>
              <th scope="col" className="hidden px-3 py-2.5 text-right sm:table-cell">
                Tokens in / out
              </th>
              <th scope="col" className="px-5 py-2.5 text-right">Cost</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100">
            {report.weeks.map((week, index) => {
              const selected = week.start === report.selected?.start
              return (
                <tr
                  key={week.start}
                  onClick={() => onSelect(week.start)}
                  className={cn('cursor-pointer transition', selected ? 'bg-brand-50/70' : 'hover:bg-slate-50')}
                >
                  <td className="px-5 py-3">
                    <button
                      type="button"
                      aria-pressed={selected}
                      onClick={(event) => {
                        event.stopPropagation()
                        onSelect(week.start)
                      }}
                      className={cn(
                        'rounded text-left font-medium whitespace-nowrap',
                        selected ? 'text-brand-800' : 'text-slate-900 hover:text-brand-700',
                      )}
                    >
                      {formatDayRange(week.start, week.end)}
                    </button>
                    {index === 0 && (
                      <Badge tone="brand" className="ml-2">
                        This week
                      </Badge>
                    )}
                  </td>
                  <td className="px-3 py-3 text-right text-slate-700 tabular-nums">
                    {formatCount(week.calls)}
                  </td>
                  <td className="hidden px-3 py-3 text-right text-slate-700 tabular-nums sm:table-cell">
                    {formatCount(week.input_tokens)} / {formatCount(week.output_tokens)}
                  </td>
                  <td className="px-5 py-3">
                    <div className="flex items-center justify-end gap-3">
                      <span aria-hidden className="hidden h-1.5 w-20 overflow-hidden rounded-full bg-slate-100 md:block">
                        <span
                          className="block h-full rounded-full bg-brand-500"
                          style={{ width: `${max > 0 ? (Number(week.cost_usd) / max) * 100 : 0}%` }}
                        />
                      </span>
                      <span className="min-w-16 text-right font-semibold text-slate-900 tabular-nums">
                        {formatUsd(week.cost_usd)}
                      </span>
                    </div>
                  </td>
                </tr>
              )
            })}
          </tbody>
        </table>
      </div>
    </Card>
  )
}

function SliceList({
  title,
  slices,
  total,
  label,
  mono = false,
}: {
  title: string
  slices: UsageSlice[]
  total: number
  label: (key: string) => string
  mono?: boolean
}) {
  return (
    <div>
      <h3 className="text-xs font-semibold text-slate-500">{title}</h3>
      <ul className="mt-2 space-y-3">
        {slices.map((slice) => (
          <li key={slice.key}>
            <div className="flex items-baseline justify-between gap-3 text-sm">
              <span className={cn('min-w-0 truncate text-slate-800', mono && 'font-mono text-xs')}>
                {label(slice.key)}
              </span>
              <span className="shrink-0 tabular-nums">
                <span className="mr-2 text-xs text-slate-500">{plural(slice.calls, 'call')}</span>
                <span className="font-semibold text-slate-900">{formatUsd(slice.cost_usd)}</span>
              </span>
            </div>
            <div aria-hidden className="mt-1.5 h-1.5 overflow-hidden rounded-full bg-slate-100">
              <div
                className="h-full rounded-full bg-brand-500"
                style={{ width: `${total > 0 ? (Number(slice.cost_usd) / total) * 100 : 0}%` }}
              />
            </div>
          </li>
        ))}
      </ul>
    </div>
  )
}

function WeekBreakdown({
  detail,
  dimmed,
}: {
  detail: NonNullable<AiUsageReport['selected']>
  dimmed: boolean
}) {
  const total = detail.by_feature.reduce((sum, slice) => sum + Number(slice.cost_usd), 0)
  return (
    <Card className={cn('transition-opacity', dimmed && 'opacity-60')}>
      <CardHeader title="Where the money went" description={formatDayRange(detail.start, detail.end)} />
      {detail.by_feature.length === 0 ? (
        <EmptyState icon={<CircleDollarSign className="size-6" />} title="No AI spend this week">
          No AI calls were made between these dates.
        </EmptyState>
      ) : (
        <div className="space-y-6 p-5">
          <SliceList title="By feature" slices={detail.by_feature} total={total} label={humanize} />
          <SliceList title="By model" slices={detail.by_model} total={total} label={(key) => key} mono />
        </div>
      )}
    </Card>
  )
}

export default function UsageTab() {
  const [week, setWeek] = useState<string | null>(null)
  const usage = useAiUsage(week)

  if (usage.isPending) {
    return (
      <div className="space-y-6">
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
          {[0, 1, 2].map((i) => (
            <Skeleton key={i} className="h-28" />
          ))}
        </div>
        <Skeleton className="h-64" />
      </div>
    )
  }
  if (usage.isError) return <Alert>{errorMessage(usage.error)}</Alert>

  const report = usage.data
  const [current, previous] = report.weeks
  return (
    <div className="space-y-6">
      <p className="max-w-3xl text-sm text-slate-600">
        Every AI call the platform makes is recorded with its cost in US dollars and kept
        permanently. Weeks run {formatWeekday(report.tracking_start)} to{' '}
        {formatWeekday(addDays(report.tracking_start, 6))} ({zoneName(report.timezone)}), starting{' '}
        {formatDay(report.tracking_start)}.
      </p>

      {current ? (
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
          <StatTile
            label="This week"
            value={formatUsd(current.cost_usd)}
            note={`${formatDayRange(current.start, current.end)} · ${plural(current.calls, 'call')}`}
          />
          <StatTile
            label="Last week"
            value={previous ? formatUsd(previous.cost_usd) : '—'}
            note={previous ? formatDayRange(previous.start, previous.end) : 'Tracking started this week'}
          />
          <StatTile
            label="Since tracking began"
            value={formatUsd(report.all_time.cost_usd)}
            note={`${plural(report.all_time.calls, 'call')} since ${formatDay(report.tracking_start)}`}
          />
        </div>
      ) : (
        <Card>
          <EmptyState icon={<CalendarClock className="size-6" />} title="Tracking hasn't started yet">
            Weekly AI spend is recorded from {formatDay(report.tracking_start)}.
          </EmptyState>
        </Card>
      )}

      <ProviderCard />

      {current && (
        <div className="grid grid-cols-1 items-start gap-6 xl:grid-cols-[minmax(0,3fr)_minmax(0,2fr)]">
          <WeeksTable
            report={report}
            onSelect={(start) => setWeek(start === current.start ? null : start)}
          />
          {report.selected && (
            <WeekBreakdown detail={report.selected} dimmed={usage.isPlaceholderData} />
          )}
        </div>
      )}
    </div>
  )
}
