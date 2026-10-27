import type { ButtonHTMLAttributes, ReactNode } from 'react'
import { Link, type LinkProps } from 'react-router'

import { cn } from '../../lib/cn'
import { Spinner } from './Feedback'

type Variant = 'primary' | 'secondary' | 'ghost' | 'danger' | 'glow'
type Size = 'sm' | 'md' | 'lg'

const VARIANTS: Record<Variant, string> = {
  primary:
    'bg-brand-600 text-white shadow-sm shadow-brand-600/25 hover:bg-brand-700 active:bg-brand-800',
  secondary:
    'bg-white text-slate-800 ring-1 ring-slate-200 ring-inset hover:bg-slate-50 hover:ring-slate-300',
  ghost: 'text-slate-700 hover:bg-slate-100',
  danger: 'bg-rose-600 text-white shadow-sm shadow-rose-600/25 hover:bg-rose-700',
  glow:
    'bg-gradient-to-r from-brand-600 via-violet-600 to-fuchsia-600 text-white shadow-lg shadow-brand-600/30 hover:shadow-xl hover:shadow-fuchsia-600/30 hover:-translate-y-0.5',
}

const SIZES: Record<Size, string> = {
  sm: 'h-8 px-3 text-sm gap-1.5 rounded-lg',
  md: 'h-10 px-4 text-sm gap-2 rounded-xl',
  lg: 'h-12 px-6 text-base gap-2 rounded-xl',
}

export function buttonClasses(variant: Variant = 'primary', size: Size = 'md', extra?: string) {
  return cn(
    'inline-flex shrink-0 items-center justify-center font-semibold whitespace-nowrap transition-all duration-200',
    'disabled:pointer-events-none disabled:opacity-55',
    VARIANTS[variant],
    SIZES[size],
    extra,
  )
}

type ButtonProps = ButtonHTMLAttributes<HTMLButtonElement> & {
  variant?: Variant
  size?: Size
  loading?: boolean
  icon?: ReactNode
}

export function Button({
  variant,
  size,
  loading = false,
  icon,
  className,
  children,
  disabled,
  type = 'button',
  ...props
}: ButtonProps) {
  return (
    <button
      type={type}
      className={buttonClasses(variant, size, className)}
      disabled={disabled || loading}
      aria-busy={loading || undefined}
      {...props}
    >
      {loading ? <Spinner className="size-4" /> : icon}
      {children}
    </button>
  )
}

export function ButtonLink({
  variant,
  size,
  className,
  ...props
}: LinkProps & { variant?: Variant; size?: Size }) {
  return <Link className={buttonClasses(variant, size, className)} {...props} />
}
