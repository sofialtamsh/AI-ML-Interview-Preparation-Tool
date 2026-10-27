import { CircleCheck, Info, LoaderCircle, TriangleAlert } from 'lucide-react'
import type { ReactNode } from 'react'

import { cn } from '../../lib/cn'

export function Spinner({ className }: { className?: string }) {
  return <LoaderCircle aria-hidden className={cn('animate-spin', className ?? 'size-5')} />
}

export function FullPageLoader({ label = 'Loading' }: { label?: string }) {
  return (
    <div className="grid min-h-dvh place-items-center" role="status" aria-label={label}>
      <Spinner className="size-7 text-brand-500" />
    </div>
  )
}

type Tone = 'error' | 'success' | 'info'

const ALERT_TONES: Record<Tone, { box: string; icon: ReactNode }> = {
  error: {
    box: 'bg-rose-50 text-rose-800 ring-rose-200',
    icon: <TriangleAlert aria-hidden className="mt-0.5 size-4 shrink-0" />,
  },
  success: {
    box: 'bg-emerald-50 text-emerald-800 ring-emerald-200',
    icon: <CircleCheck aria-hidden className="mt-0.5 size-4 shrink-0" />,
  },
  info: {
    box: 'bg-brand-50 text-brand-900 ring-brand-200',
    icon: <Info aria-hidden className="mt-0.5 size-4 shrink-0" />,
  },
}

export function Alert({
  tone = 'error',
  children,
  className,
}: {
  tone?: Tone
  children: ReactNode
  className?: string
}) {
  const style = ALERT_TONES[tone]
  return (
    <div
      role={tone === 'error' ? 'alert' : 'status'}
      className={cn(
        'flex animate-pop gap-2.5 rounded-xl px-3.5 py-3 text-sm ring-1 ring-inset',
        style.box,
        className,
      )}
    >
      {style.icon}
      <div className="min-w-0">{children}</div>
    </div>
  )
}

export function EmptyState({
  icon,
  title,
  children,
  action,
  className,
}: {
  icon: ReactNode
  title: string
  children?: ReactNode
  action?: ReactNode
  className?: string
}) {
  return (
    <div className={cn('flex flex-col items-center px-6 py-12 text-center', className)}>
      <div className="mb-4 grid size-14 place-items-center rounded-2xl bg-gradient-to-br from-brand-50 to-fuchsia-50 text-brand-600 ring-1 ring-brand-100">
        {icon}
      </div>
      <h3 className="font-display text-lg font-semibold text-slate-900">{title}</h3>
      {children && <div className="mt-1.5 max-w-md text-sm text-slate-600">{children}</div>}
      {action && <div className="mt-5">{action}</div>}
    </div>
  )
}

export function Skeleton({ className }: { className?: string }) {
  return (
    <div
      aria-hidden
      className={cn(
        'animate-shimmer rounded-lg bg-[length:200%_100%] bg-gradient-to-r from-slate-100 via-slate-200/70 to-slate-100',
        className,
      )}
    />
  )
}

type BadgeTone = 'neutral' | 'brand' | 'success' | 'warning' | 'danger'

const BADGE_TONES: Record<BadgeTone, string> = {
  neutral: 'bg-slate-100 text-slate-700 ring-slate-200',
  brand: 'bg-brand-50 text-brand-700 ring-brand-200',
  success: 'bg-emerald-50 text-emerald-700 ring-emerald-200',
  warning: 'bg-amber-50 text-amber-800 ring-amber-200',
  danger: 'bg-rose-50 text-rose-700 ring-rose-200',
}

export function Badge({
  tone = 'neutral',
  children,
  className,
}: {
  tone?: BadgeTone
  children: ReactNode
  className?: string
}) {
  return (
    <span
      className={cn(
        'inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-xs font-medium whitespace-nowrap ring-1 ring-inset',
        BADGE_TONES[tone],
        className,
      )}
    >
      {children}
    </span>
  )
}

export function Card({ className, children }: { className?: string; children: ReactNode }) {
  return (
    <section
      className={cn('rounded-2xl bg-white shadow-sm ring-1 ring-slate-200/80', className)}
    >
      {children}
    </section>
  )
}

export function CardHeader({
  title,
  description,
  action,
}: {
  title: string
  description?: ReactNode
  action?: ReactNode
}) {
  return (
    <div className="flex flex-wrap items-start justify-between gap-3 border-b border-slate-100 px-5 py-4">
      <div>
        <h2 className="font-display text-base font-semibold text-slate-900">{title}</h2>
        {description && <p className="mt-0.5 text-sm text-slate-500">{description}</p>}
      </div>
      {action}
    </div>
  )
}

export function PageHeader({
  title,
  description,
  actions,
}: {
  title: string
  description?: ReactNode
  actions?: ReactNode
}) {
  return (
    <div className="mb-6 flex flex-wrap items-end justify-between gap-4">
      <div>
        <h1 className="font-display text-2xl font-bold tracking-tight text-slate-900 sm:text-3xl">
          {title}
        </h1>
        {description && <p className="mt-1 text-sm text-slate-600">{description}</p>}
      </div>
      {actions && <div className="flex flex-wrap gap-2">{actions}</div>}
    </div>
  )
}
