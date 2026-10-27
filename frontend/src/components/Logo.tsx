import { useId } from 'react'

import { BRAND } from '../brand'
import { cn } from '../lib/cn'

export function LogoMark({ className }: { className?: string }) {
  // Unique per instance: a gradient defined inside a display:none copy (e.g. the desktop
  // sidebar on mobile) would otherwise blank out every other logo on the page.
  const gradientId = `logo-${useId().replace(/[^\w-]/g, '')}`
  return (
    <svg viewBox="0 0 32 32" aria-hidden className={cn('size-8', className)}>
      <defs>
        <linearGradient id={gradientId} x1="0" y1="0" x2="1" y2="1">
          <stop offset="0" stopColor="#7c4dff" />
          <stop offset="1" stopColor="#d946ef" />
        </linearGradient>
      </defs>
      <rect width="32" height="32" rx="9" fill={`url(#${gradientId})`} />
      <path
        d="M9 21.5 15.5 10.5 22.5 19"
        fill="none"
        stroke="#fff"
        strokeWidth="2"
        strokeLinecap="round"
        strokeLinejoin="round"
        opacity=".75"
      />
      <circle cx="9" cy="21.5" r="3" fill="#fff" />
      <circle cx="15.5" cy="10.5" r="3" fill="#fff" />
      <circle cx="22.5" cy="19" r="3" fill="#bef264" />
    </svg>
  )
}

export function Logo({ tone = 'dark', suffix }: { tone?: 'dark' | 'light'; suffix?: string }) {
  return (
    <span className="inline-flex items-center gap-2.5">
      <LogoMark />
      <span
        className={cn(
          'font-display text-[15px] leading-tight font-bold tracking-tight',
          tone === 'light' ? 'text-white' : 'text-slate-900',
        )}
      >
        {BRAND.name}
        {suffix && (
          <span
            className={cn(
              'block text-[11px] font-medium tracking-wide uppercase',
              tone === 'light' ? 'text-white/60' : 'text-slate-500',
            )}
          >
            {suffix}
          </span>
        )}
      </span>
    </span>
  )
}
