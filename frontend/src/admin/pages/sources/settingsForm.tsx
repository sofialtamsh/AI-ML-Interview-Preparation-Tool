/** Renders a source's settings from the backend's field descriptions (FieldSpec). */

import { PasswordField, SelectField, TextAreaField, TextField } from '../../../components/ui/Field'
import type { FieldSpec } from '../../../lib/types'

export type FormValues = Record<string, unknown>

function emptyValue(field: FieldSpec): unknown {
  if (field.kind === 'checkbox') return false
  if (field.kind === 'lines') return []
  return ''
}

/** Form state for these fields: current values where known, else the backend defaults. */
export function initialValues(fields: FieldSpec[], current?: Record<string, unknown>): FormValues {
  return Object.fromEntries(
    fields.map((field) => {
      const value = current?.[field.key] ?? field.default ?? emptyValue(field)
      return [field.key, field.kind === 'number' && value !== '' ? String(value) : value]
    }),
  )
}

export function isVisible(field: FieldSpec, values: FormValues): boolean {
  if (!field.visible_when) return true
  return Object.entries(field.visible_when).every(([key, allowed]) => {
    const raw = values[key]
    const value = Array.isArray(raw) ? raw.join('\n') : String(raw ?? '')
    return allowed.includes('*') ? value.trim() !== '' : allowed.includes(value)
  })
}

/** The JSON the API expects: numbers as numbers, lines as trimmed non-empty strings. */
export function toPayload(fields: FieldSpec[], values: FormValues): Record<string, unknown> {
  return Object.fromEntries(
    fields.map((field) => {
      const value = values[field.key]
      if (field.kind === 'number') {
        return [field.key, value === '' || value == null ? field.default : Number(value)]
      }
      if (field.kind === 'lines') {
        const lines = Array.isArray(value) ? value : String(value ?? '').split('\n')
        return [field.key, lines.map((line) => String(line).trim()).filter(Boolean)]
      }
      return [field.key, value]
    }),
  )
}

export function SettingsFields({
  fields,
  values,
  onChange,
  errors,
}: {
  fields: FieldSpec[]
  values: FormValues
  onChange: (key: string, value: unknown) => void
  errors: Record<string, string>
}) {
  return (
    <>
      {fields
        .filter((field) => isVisible(field, values))
        .map((field) => (
          <SettingInput
            key={field.key}
            field={field}
            value={values[field.key]}
            onChange={(value) => onChange(field.key, value)}
            error={errors[field.key]}
          />
        ))}
    </>
  )
}

function SettingInput({
  field,
  value,
  onChange,
  error,
}: {
  field: FieldSpec
  value: unknown
  onChange: (value: unknown) => void
  error?: string
}) {
  const label = field.label
  const hint = field.help || undefined
  switch (field.kind) {
    case 'checkbox':
      return (
        <label className="flex cursor-pointer gap-3 rounded-xl p-3 ring-1 ring-slate-200 has-[:checked]:bg-brand-50/50 has-[:checked]:ring-brand-200">
          <input
            type="checkbox"
            className="mt-0.5 size-4 accent-brand-600"
            checked={value === true}
            onChange={(e) => onChange(e.target.checked)}
          />
          <span>
            <span className="block text-sm font-medium text-slate-900">{field.label}</span>
            {field.help && <span className="block text-xs text-slate-500">{field.help}</span>}
            {error && <span className="block text-xs font-medium text-rose-600">{error}</span>}
          </span>
        </label>
      )
    case 'select':
      return (
        <SelectField
          label={label}
          hint={hint}
          error={error}
          value={String(value ?? '')}
          onChange={(e) => onChange(e.target.value)}
        >
          {field.options?.map((option) => (
            <option key={option.value} value={option.value}>
              {option.label}
            </option>
          ))}
        </SelectField>
      )
    case 'textarea':
    case 'lines':
      return (
        <TextAreaField
          label={label}
          hint={hint}
          error={error}
          placeholder={field.placeholder}
          value={Array.isArray(value) ? value.join('\n') : String(value ?? '')}
          onChange={(e) =>
            onChange(field.kind === 'lines' ? e.target.value.split('\n') : e.target.value)
          }
          className={field.kind === 'lines' ? 'font-mono text-xs' : undefined}
        />
      )
    case 'password':
      return (
        <PasswordField
          label={label}
          hint={hint}
          error={error}
          value={String(value ?? '')}
          onChange={(e) => onChange(e.target.value)}
          autoComplete="off"
        />
      )
    default:
      return (
        <TextField
          label={label}
          hint={hint}
          error={error}
          type={field.kind === 'number' ? 'number' : field.kind === 'url' ? 'url' : 'text'}
          inputMode={field.kind === 'number' ? 'decimal' : undefined}
          min={field.min ?? undefined}
          max={field.max ?? undefined}
          step={field.kind === 'number' ? 'any' : undefined}
          placeholder={field.placeholder}
          value={String(value ?? '')}
          onChange={(e) => onChange(e.target.value)}
          spellCheck={false}
        />
      )
  }
}
