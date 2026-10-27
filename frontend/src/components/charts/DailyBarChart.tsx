import { useEffect, useRef, useState, type KeyboardEvent } from 'react'

import type { DailyCount } from '../../lib/types'

const HEIGHT = 200
const PAD = { top: 12, right: 8, bottom: 26, left: 34 }
const MAX_BAR = 24
const GAP = 2
const RADIUS = 4

const dayLabel = new Intl.DateTimeFormat(undefined, { day: 'numeric', month: 'short' })
const longDayLabel = new Intl.DateTimeFormat(undefined, {
  weekday: 'short',
  day: 'numeric',
  month: 'short',
})
const parseDay = (day: string) => new Date(`${day}T00:00:00`)

/** Clean integer ticks: 0..max in at most 4 steps of 1, 2, 5, 10, 20, 50... */
export function integerTicks(max: number): number[] {
  const target = Math.max(max, 4)
  const raw = target / 4
  const magnitude = 10 ** Math.floor(Math.log10(raw))
  const step = [1, 2, 5, 10].map((m) => m * magnitude).find((s) => s >= raw) ?? 10 * magnitude
  const top = Math.ceil(target / step) * step
  return Array.from({ length: top / step + 1 }, (_, i) => i * step)
}

function barPath(x: number, y: number, w: number, h: number): string {
  const r = Math.min(RADIUS, w / 2, h)
  return `M${x},${y + h} V${y + r} Q${x},${y} ${x + r},${y} H${x + w - r} Q${x + w},${y} ${x + w},${y + r} V${y + h} Z`
}

function useWidth<T extends HTMLElement>() {
  const ref = useRef<T>(null)
  const [width, setWidth] = useState(640)
  useEffect(() => {
    const el = ref.current
    if (!el || typeof ResizeObserver === 'undefined') return
    const observer = new ResizeObserver(([entry]) => setWidth(entry.contentRect.width))
    observer.observe(el)
    return () => observer.disconnect()
  }, [])
  return [ref, width] as const
}

export function DailyBarChart({ data, label }: { data: DailyCount[]; label: string }) {
  const [ref, width] = useWidth<HTMLDivElement>()
  const [active, setActive] = useState<number | null>(null)

  const ticks = integerTicks(Math.max(0, ...data.map((d) => d.count)))
  const yMax = ticks.at(-1)!
  const plotW = Math.max(0, width - PAD.left - PAD.right)
  const plotH = HEIGHT - PAD.top - PAD.bottom
  const band = data.length ? plotW / data.length : 0
  const barW = Math.max(2, Math.min(MAX_BAR, band - GAP))
  const y = (v: number) => PAD.top + plotH - (v / yMax) * plotH
  // Roughly one date label per 72px, so narrow screens don't crowd the axis.
  const labelEvery = Math.ceil(data.length / Math.max(2, Math.min(6, Math.floor(plotW / 72))))
  const labelPosition = (i: number): { x: number; anchor: 'start' | 'middle' | 'end' } => {
    const barX = PAD.left + band * i + (band - barW) / 2
    if (i === 0) return { x: barX, anchor: 'start' }
    if (i === data.length - 1) return { x: barX + barW, anchor: 'end' }
    return { x: barX + barW / 2, anchor: 'middle' }
  }

  const onKeyDown = (event: KeyboardEvent) => {
    if (!data.length) return
    if (event.key === 'ArrowRight' || event.key === 'ArrowLeft') {
      event.preventDefault()
      const delta = event.key === 'ArrowRight' ? 1 : -1
      setActive((i) => Math.min(data.length - 1, Math.max(0, (i ?? data.length) + delta)))
    } else if (event.key === 'Escape') {
      setActive(null)
    }
  }

  const point = active !== null ? data[active] : null
  const tooltipX = active !== null ? PAD.left + band * active + band / 2 : 0

  return (
    <div>
      <div
        ref={ref}
        className="relative w-full min-w-0 outline-none focus-visible:rounded-xl focus-visible:ring-2 focus-visible:ring-brand-500"
        tabIndex={0}
        role="group"
        aria-label={`${label}. Use left and right arrow keys to read each day.`}
        onKeyDown={onKeyDown}
        onBlur={() => setActive(null)}
        onPointerLeave={() => setActive(null)}
      >
        {/* Fluid width: a fixed pixel width would stop narrow containers from shrinking. */}
        <svg
          width="100%"
          height={HEIGHT}
          viewBox={`0 0 ${width} ${HEIGHT}`}
          preserveAspectRatio="none"
          aria-hidden
          className="block"
        >
          {ticks.map((t) => (
            <g key={t}>
              <line
                x1={PAD.left}
                x2={width - PAD.right}
                y1={y(t)}
                y2={y(t)}
                stroke={t === 0 ? '#cbd5e1' : '#e2e8f0'}
                strokeWidth="1"
                shapeRendering="crispEdges"
              />
              <text
                x={PAD.left - 8}
                y={y(t)}
                dy="0.32em"
                textAnchor="end"
                className="fill-slate-500 text-[11px] tabular-nums"
              >
                {t}
              </text>
            </g>
          ))}
          {data.map((d, i) => {
            const x = PAD.left + band * i + (band - barW) / 2
            const h = (d.count / yMax) * plotH
            return (
              <g key={d.day}>
                {h > 0 && (
                  <path
                    d={barPath(x, y(d.count), barW, h)}
                    className={
                      active === i ? 'fill-brand-400 transition-colors' : 'fill-brand-500 transition-colors'
                    }
                  />
                )}
                <rect
                  x={PAD.left + band * i}
                  y={PAD.top}
                  width={band}
                  height={plotH}
                  fill="transparent"
                  onPointerEnter={() => setActive(i)}
                />
                {(i % labelEvery === 0 || i === data.length - 1) &&
                  (i === data.length - 1 || data.length - 1 - i >= labelEvery / 2) && (
                    <text
                      x={labelPosition(i).x}
                      y={HEIGHT - 8}
                      textAnchor={labelPosition(i).anchor}
                      className="fill-slate-500 text-[11px]"
                    >
                      {dayLabel.format(parseDay(d.day))}
                    </text>
                  )}
              </g>
            )
          })}
        </svg>
        {point && (
          <div
            role="status"
            className="pointer-events-none absolute top-0 z-10 -translate-x-1/2 rounded-xl bg-slate-900 px-3 py-2 text-center whitespace-nowrap text-white shadow-lg"
            style={{ left: Math.min(Math.max(tooltipX, 70), width - 70) }}
          >
            <p className="text-sm font-semibold">
              {point.count} registration{point.count === 1 ? '' : 's'}
            </p>
            <p className="text-xs text-slate-300">{longDayLabel.format(parseDay(point.day))}</p>
          </div>
        )}
      </div>
      <details className="mt-3 text-sm">
        <summary className="cursor-pointer text-xs font-medium text-slate-500 hover:text-slate-800">
          View as table
        </summary>
        <div className="mt-2 max-h-56 overflow-y-auto rounded-xl ring-1 ring-slate-200">
          <table className="w-full text-left text-sm">
            <caption className="sr-only">{label}</caption>
            <thead className="sticky top-0 bg-slate-50 text-xs text-slate-500">
              <tr>
                <th className="px-3 py-2 font-medium">Day</th>
                <th className="px-3 py-2 text-right font-medium">Registrations</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {data.map((d) => (
                <tr key={d.day}>
                  <td className="px-3 py-1.5">{longDayLabel.format(parseDay(d.day))}</td>
                  <td className="px-3 py-1.5 text-right tabular-nums">{d.count}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </details>
    </div>
  )
}
