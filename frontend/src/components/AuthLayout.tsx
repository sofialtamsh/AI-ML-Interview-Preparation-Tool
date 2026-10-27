import type { ReactNode } from 'react'
import { Link } from 'react-router'

import { cn } from '../lib/cn'
import { GradientDescentHero } from './GradientDescentHero'
import { Logo } from './Logo'

type Variant = 'student' | 'admin'

const PANEL: Record<Variant, { heading: ReactNode; body: string; className: string }> = {
  student: {
    heading: (
      <>
        Learn it. <span className="text-lime-300">See it.</span> Crack the interview.
      </>
    ),
    body: 'Concepts you can play with, real interview patterns, and progress that follows you across devices.',
    className: 'from-brand-950 via-[#1d0b4d] to-slate-950',
  },
  admin: {
    heading: 'Admin console',
    body: 'Manage students, content and interview intelligence. Every action here is permission-checked and audited.',
    className: 'from-slate-950 via-slate-900 to-brand-950',
  },
}

export function AuthLayout({
  variant = 'student',
  title,
  subtitle,
  children,
  footer,
}: {
  variant?: Variant
  title: string
  subtitle?: ReactNode
  children: ReactNode
  footer?: ReactNode
}) {
  const panel = PANEL[variant]
  return (
    <div className="grid min-h-dvh lg:grid-cols-[minmax(0,1fr)_minmax(0,1.05fr)]">
      <main className="flex flex-col px-5 py-8 sm:px-10">
        <Link to={variant === 'admin' ? '/admin' : '/'} className="self-start rounded-lg">
          <Logo suffix={variant === 'admin' ? 'Admin console' : undefined} />
        </Link>
        <div className="mx-auto flex w-full max-w-sm flex-1 flex-col justify-center py-10">
          <div className="animate-fade-up">
            <h1 className="font-display text-3xl font-bold tracking-tight text-slate-900">
              {title}
            </h1>
            {subtitle && <p className="mt-2 text-sm text-slate-600">{subtitle}</p>}
            <div className="mt-8">{children}</div>
            {footer && <div className="mt-8 text-sm text-slate-600">{footer}</div>}
          </div>
        </div>
      </main>

      <aside
        className={cn(
          'relative hidden overflow-hidden bg-gradient-to-br lg:flex lg:flex-col lg:justify-center lg:px-14',
          panel.className,
        )}
      >
        <div
          aria-hidden
          className="absolute -top-24 -right-24 size-96 animate-float rounded-full bg-fuchsia-500/25 blur-3xl"
        />
        <div
          aria-hidden
          className="absolute -bottom-32 -left-16 size-96 animate-float rounded-full bg-brand-500/30 blur-3xl [animation-delay:-4s]"
        />
        <div
          aria-hidden
          className="absolute inset-0 bg-[linear-gradient(rgba(255,255,255,0.04)_1px,transparent_1px),linear-gradient(90deg,rgba(255,255,255,0.04)_1px,transparent_1px)] bg-[size:44px_44px]"
        />
        <div className="relative max-w-lg">
          <h2 className="font-display text-4xl leading-tight font-bold text-white">
            {panel.heading}
          </h2>
          <p className="mt-4 text-base text-violet-100/80">{panel.body}</p>
          <div className="mt-10 rounded-3xl bg-white/[0.06] p-6 ring-1 ring-white/10 backdrop-blur">
            <p className="mb-2 text-xs font-semibold tracking-widest text-violet-200/70 uppercase">
              Gradient descent, live
            </p>
            <GradientDescentHero />
          </div>
        </div>
      </aside>
    </div>
  )
}
