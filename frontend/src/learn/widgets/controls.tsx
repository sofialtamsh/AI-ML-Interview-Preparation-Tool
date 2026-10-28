import { useId, type ReactNode } from 'react'

import { cn } from '../../lib/cn'

/** The shared layout: the visual on the left (top on phones), controls beside it. */
export function WidgetFrame({ plot, controls, below }: { plot: ReactNode; controls: ReactNode; below?: ReactNode }) {
  return (
    <div className="grid items-start gap-4 lg:grid-cols-[minmax(0,1fr)_17rem]">
      <div className="min-w-0 space-y-3">
        <div className="overflow-hidden rounded-2xl bg-white ring-1 ring-slate-200">{plot}</div>
        {below}
      </div>
      <div className="space-y-4 rounded-2xl bg-slate-50 p-4 ring-1 ring-slate-200/80">{controls}</div>
    </div>
  )
}

export function Slider({
  label,
  value,
  min,
  max,
  step = 1,
  onChange,
  format,
  disabled,
}: {
  label: string
  value: number
  min: number
  max: number
  step?: number
  onChange: (value: number) => void
  format?: (value: number) => string
  disabled?: boolean
}) {
  const id = useId()
  return (
    <div>
      <div className="flex items-baseline justify-between gap-2 text-xs font-semibold text-slate-600">
        <label htmlFor={id}>{label}</label>
        <output htmlFor={id} className="font-mono text-sm text-slate-900 tabular-nums">
          {format ? format(value) : value}
        </output>
      </div>
      <input
        id={id}
        type="range"
        min={min}
        max={max}
        step={step}
        value={value}
        disabled={disabled}
        onChange={(event) => onChange(Number(event.target.value))}
        className="mt-1.5 h-6 w-full cursor-pointer accent-brand-600 disabled:cursor-not-allowed disabled:opacity-50"
      />
    </div>
  )
}

export function Choice<T extends string | number>({
  label,
  value,
  options,
  onChange,
}: {
  label: string
  value: T
  options: { value: T; label: ReactNode; swatch?: string }[]
  onChange: (value: T) => void
}) {
  return (
    <fieldset>
      <legend className="text-xs font-semibold text-slate-600">{label}</legend>
      <div className="mt-1.5 flex flex-wrap gap-1.5">
        {options.map((option) => {
          const active = option.value === value
          return (
            <button
              key={String(option.value)}
              type="button"
              aria-pressed={active}
              onClick={() => onChange(option.value)}
              className={cn(
                'inline-flex h-8 items-center gap-1.5 rounded-lg px-2.5 text-xs font-semibold transition',
                active
                  ? 'bg-slate-900 text-white shadow-sm'
                  : 'bg-white text-slate-700 ring-1 ring-slate-200 ring-inset hover:bg-slate-100',
              )}
            >
              {option.swatch && (
                <span aria-hidden className="size-2.5 rounded-full ring-1 ring-white/60" style={{ background: option.swatch }} />
              )}
              {option.label}
            </button>
          )
        })}
      </div>
    </fieldset>
  )
}

export function Toggle({ label, checked, onChange, disabled }: { label: string; checked: boolean; onChange: (value: boolean) => void; disabled?: boolean }) {
  return (
    <button
      type="button"
      role="switch"
      aria-checked={checked}
      disabled={disabled}
      onClick={() => onChange(!checked)}
      className="flex w-full items-center justify-between gap-3 text-left text-sm font-medium text-slate-700 disabled:opacity-50"
    >
      {label}
      <span className={cn('relative h-5 w-9 shrink-0 rounded-full transition', checked ? 'bg-brand-600' : 'bg-slate-300')}>
        <span className={cn('absolute top-0.5 size-4 rounded-full bg-white shadow transition-all', checked ? 'left-[1.125rem]' : 'left-0.5')} />
      </span>
    </button>
  )
}

export function Readouts({ items }: { items: { label: string; value: ReactNode; note?: ReactNode }[] }) {
  return (
    <dl className="grid grid-cols-2 gap-2">
      {items.map((item) => (
        <div key={item.label} className="rounded-xl bg-white px-3 py-2 ring-1 ring-slate-200/80">
          <dt className="text-[11px] font-semibold tracking-wide text-slate-500 uppercase">{item.label}</dt>
          <dd className="font-mono text-lg font-semibold text-slate-900 tabular-nums">{item.value}</dd>
          {item.note && <dd className="text-[11px] text-slate-500">{item.note}</dd>}
        </div>
      ))}
    </dl>
  )
}

export function ButtonRow({ children }: { children: ReactNode }) {
  return <div className="flex flex-wrap gap-2">{children}</div>
}

/** A legend entry: a mark plus text in ink colour (never coloured text). */
export function Legend({ items }: { items: { label: string; mark: ReactNode }[] }) {
  return (
    <ul className="flex flex-wrap gap-x-4 gap-y-1 px-1 text-xs text-slate-600">
      {items.map((item) => (
        <li key={item.label} className="inline-flex items-center gap-1.5">
          {item.mark}
          {item.label}
        </li>
      ))}
    </ul>
  )
}

export const Dot = ({ color, hollow }: { color: string; hollow?: boolean }) => (
  <span
    aria-hidden
    className="inline-block size-2.5 rounded-full"
    style={hollow ? { boxShadow: `inset 0 0 0 2px ${color}` } : { background: color }}
  />
)

export const Line = ({ color, dashed }: { color: string; dashed?: boolean }) => (
  <span aria-hidden className="inline-block w-4 border-t-2" style={{ borderColor: color, borderStyle: dashed ? 'dashed' : 'solid' }} />
)

export function Hint({ children }: { children: ReactNode }) {
  return <p className="text-xs text-slate-500">{children}</p>
}
