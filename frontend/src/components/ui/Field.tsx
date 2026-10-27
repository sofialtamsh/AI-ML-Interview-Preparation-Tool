import { Eye, EyeOff } from 'lucide-react'
import {
  useId,
  useState,
  type InputHTMLAttributes,
  type ReactNode,
  type SelectHTMLAttributes,
  type TextareaHTMLAttributes,
} from 'react'

import { cn } from '../../lib/cn'

const CONTROL =
  'block w-full rounded-xl border-0 bg-white px-3.5 py-2.5 text-sm text-slate-900 shadow-xs ring-1 ring-slate-300 ring-inset transition placeholder:text-slate-400 focus:ring-2 focus:ring-brand-500 focus:outline-none disabled:bg-slate-50 disabled:text-slate-500'

type FieldShellProps = {
  id: string
  label: string
  hint?: ReactNode
  error?: string
  children: ReactNode
  labelAction?: ReactNode
}

function FieldShell({ id, label, hint, error, children, labelAction }: FieldShellProps) {
  return (
    <div>
      <div className="mb-1.5 flex items-center justify-between gap-2">
        <label htmlFor={id} className="text-sm font-medium text-slate-800">
          {label}
        </label>
        {labelAction}
      </div>
      {children}
      {error ? (
        <p id={`${id}-error`} className="mt-1.5 text-xs font-medium text-rose-600">
          {error}
        </p>
      ) : (
        hint && (
          <p id={`${id}-hint`} className="mt-1.5 text-xs text-slate-500">
            {hint}
          </p>
        )
      )}
    </div>
  )
}

type TextFieldProps = InputHTMLAttributes<HTMLInputElement> & {
  label: string
  hint?: ReactNode
  error?: string
  labelAction?: ReactNode
}

export function TextField({ label, hint, error, labelAction, className, ...props }: TextFieldProps) {
  const id = useId()
  return (
    <FieldShell id={id} label={label} hint={hint} error={error} labelAction={labelAction}>
      <input
        id={id}
        className={cn(CONTROL, error && 'ring-rose-400', className)}
        aria-invalid={!!error || undefined}
        aria-describedby={error ? `${id}-error` : hint ? `${id}-hint` : undefined}
        {...props}
      />
    </FieldShell>
  )
}

export function PasswordField({
  label,
  hint,
  error,
  labelAction,
  className,
  ...props
}: TextFieldProps) {
  const id = useId()
  const [visible, setVisible] = useState(false)
  return (
    <FieldShell id={id} label={label} hint={hint} error={error} labelAction={labelAction}>
      <div className="relative">
        <input
          id={id}
          type={visible ? 'text' : 'password'}
          className={cn(CONTROL, 'pr-11', error && 'ring-rose-400', className)}
          aria-invalid={!!error || undefined}
          aria-describedby={error ? `${id}-error` : hint ? `${id}-hint` : undefined}
          {...props}
        />
        <button
          type="button"
          onClick={() => setVisible((v) => !v)}
          className="absolute inset-y-0 right-0 grid w-11 place-items-center rounded-r-xl text-slate-400 transition hover:text-slate-700"
          aria-label={visible ? 'Hide password' : 'Show password'}
          aria-pressed={visible}
        >
          {visible ? <EyeOff className="size-4" /> : <Eye className="size-4" />}
        </button>
      </div>
    </FieldShell>
  )
}

type TextAreaFieldProps = TextareaHTMLAttributes<HTMLTextAreaElement> & {
  label: string
  hint?: ReactNode
  error?: string
}

export function TextAreaField({ label, hint, error, className, ...props }: TextAreaFieldProps) {
  const id = useId()
  return (
    <FieldShell id={id} label={label} hint={hint} error={error}>
      <textarea
        id={id}
        rows={3}
        className={cn(CONTROL, 'resize-y', error && 'ring-rose-400', className)}
        aria-invalid={!!error || undefined}
        aria-describedby={error ? `${id}-error` : hint ? `${id}-hint` : undefined}
        {...props}
      />
    </FieldShell>
  )
}

type SelectFieldProps = SelectHTMLAttributes<HTMLSelectElement> & {
  label: string
  hint?: ReactNode
  error?: string
  hideLabel?: boolean
}

export function SelectField({
  label,
  hint,
  error,
  hideLabel,
  className,
  children,
  ...props
}: SelectFieldProps) {
  const id = useId()
  const select = (
    <select
      id={id}
      className={cn(CONTROL, 'pr-9', className)}
      aria-label={hideLabel ? label : undefined}
      {...props}
    >
      {children}
    </select>
  )
  if (hideLabel) return select
  return (
    <FieldShell id={id} label={label} hint={hint} error={error}>
      {select}
    </FieldShell>
  )
}
