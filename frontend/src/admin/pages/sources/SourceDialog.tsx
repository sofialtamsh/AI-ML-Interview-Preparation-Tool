import { useState, type FormEvent } from 'react'

import { Button } from '../../../components/ui/Button'
import { Dialog } from '../../../components/ui/Dialog'
import { Alert } from '../../../components/ui/Feedback'
import { SelectField, TextAreaField, TextField } from '../../../components/ui/Field'
import { ApiError, errorMessage } from '../../../lib/api'
import { cn } from '../../../lib/cn'
import type { AuthMethod, ConnectorType, SourceCatalog, SourceDetail } from '../../../lib/types'
import { useSaveSource } from '../../api'
import { initialValues, SettingsFields, toPayload, type FormValues } from './settingsForm'
import { CONNECTOR_ICONS } from './shared'

function TypePicker({
  catalog,
  value,
  onChange,
}: {
  catalog: SourceCatalog
  value: ConnectorType
  onChange: (type: ConnectorType) => void
}) {
  return (
    <fieldset>
      <legend className="mb-2 text-sm font-medium text-slate-800">What kind of source?</legend>
      <div className="grid gap-2 sm:grid-cols-2">
        {catalog.connectors.map((connector) => {
          const Icon = CONNECTOR_ICONS[connector.key]
          return (
            <label
              key={connector.key}
              className={cn(
                'flex cursor-pointer gap-3 rounded-xl p-3 ring-1 ring-slate-200 transition',
                'has-[:checked]:bg-brand-50/60 has-[:checked]:ring-2 has-[:checked]:ring-brand-400',
                'has-[:focus-visible]:ring-2 has-[:focus-visible]:ring-brand-500',
              )}
            >
              <input
                type="radio"
                name="connector"
                className="sr-only"
                checked={value === connector.key}
                onChange={() => onChange(connector.key)}
              />
              <Icon className="mt-0.5 size-5 shrink-0 text-brand-600" aria-hidden />
              <span>
                <span className="block text-sm font-semibold text-slate-900">{connector.label}</span>
                <span className="block text-xs text-slate-500">{connector.description}</span>
              </span>
            </label>
          )
        })}
      </div>
    </fieldset>
  )
}

export function SourceDialog({
  catalog,
  source,
  onClose,
  onSaved,
}: {
  catalog: SourceCatalog
  source: SourceDetail | null
  onClose: () => void
  onSaved: (saved: SourceDetail) => void
}) {
  const [type, setType] = useState<ConnectorType>(source?.connector_type ?? 'web_pages')
  const connector = catalog.connectors.find((c) => c.key === type)!
  const [name, setName] = useState(source?.name ?? '')
  const [description, setDescription] = useState(source?.description ?? '')
  const [baseUrl, setBaseUrl] = useState(source?.base_url ?? '')
  const [authMethod, setAuthMethod] = useState<AuthMethod>(source?.auth_method ?? 'none')
  const [enabled, setEnabled] = useState(source?.enabled ?? true)
  const [settings, setSettings] = useState<FormValues>(() =>
    initialValues(connector.settings_fields, source?.config),
  )
  const auth = catalog.auth_methods.find((m) => m.key === authMethod)!
  const [authSettings, setAuthSettings] = useState<FormValues>(() =>
    initialValues(auth.settings_fields, source?.auth_config),
  )
  const save = useSaveSource(source?.id ?? null)
  const errors = save.error instanceof ApiError ? save.error.fieldErrors : {}

  const chooseType = (next: ConnectorType) => {
    const nextConnector = catalog.connectors.find((c) => c.key === next)!
    setType(next)
    setSettings(initialValues(nextConnector.settings_fields))
    if (!nextConnector.auth_methods.includes(authMethod)) chooseAuth('none')
  }

  const chooseAuth = (next: AuthMethod) => {
    setAuthMethod(next)
    const nextAuth = catalog.auth_methods.find((m) => m.key === next)!
    setAuthSettings(
      initialValues(nextAuth.settings_fields, next === source?.auth_method ? source.auth_config : undefined),
    )
  }

  const submit = (event: FormEvent) => {
    event.preventDefault()
    save.mutate(
      {
        name: name.trim(),
        description: description.trim(),
        ...(source ? {} : { connector_type: type }),
        base_url: connector.uses_url ? baseUrl.trim() : null,
        auth_method: authMethod,
        config: toPayload(connector.settings_fields, settings),
        auth_config: toPayload(auth.settings_fields, authSettings),
        enabled,
      },
      { onSuccess: onSaved },
    )
  }

  const sentence = auth.secret_fields.length
    ? `You'll add the ${auth.secret_fields.map((f) => f.label.toLowerCase()).join(' and ')} after saving. They're stored encrypted.`
    : null

  return (
    <Dialog
      open
      onClose={onClose}
      size="lg"
      title={source ? `Edit ${source.name}` : 'Add an interview source'}
      description={
        source
          ? 'Changing the URL or sign-in resets the connection status.'
          : 'Nothing is fetched until you press Fetch.'
      }
      footer={
        <>
          <Button variant="secondary" onClick={onClose}>
            Cancel
          </Button>
          <Button
            type="submit"
            form="source-form"
            loading={save.isPending}
            disabled={name.trim().length < 2 || (connector.uses_url && !baseUrl.trim())}
          >
            {source ? 'Save changes' : 'Add source'}
          </Button>
        </>
      }
    >
      <form id="source-form" onSubmit={submit} className="space-y-6">
        {save.isError && <Alert>{errorMessage(save.error)}</Alert>}
        {!source && <TypePicker catalog={catalog} value={type} onChange={chooseType} />}

        <section className="space-y-4">
          <div className="grid gap-4 sm:grid-cols-2">
            <TextField
              label="Name"
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="e.g. Partner interview portal"
              error={errors.name}
              maxLength={120}
            />
            {connector.uses_url && (
              <TextField
                label="Base URL"
                type="url"
                value={baseUrl}
                onChange={(e) => setBaseUrl(e.target.value)}
                placeholder="https://example.com"
                error={errors.base_url}
                spellCheck={false}
              />
            )}
          </div>
          <TextAreaField
            label="Notes (optional)"
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            placeholder="What this source has, who granted access, any terms of use"
            rows={2}
          />
        </section>

        {connector.uses_url && (
          <section className="space-y-4 rounded-2xl bg-slate-50/80 p-4 ring-1 ring-slate-200/70">
            <h3 className="text-sm font-semibold text-slate-900">Sign-in</h3>
            <SelectField
              label="How the platform signs in"
              value={authMethod}
              onChange={(e) => chooseAuth(e.target.value as AuthMethod)}
              hint={auth.description}
            >
              {catalog.auth_methods
                .filter((m) => connector.auth_methods.includes(m.key))
                .map((m) => (
                  <option key={m.key} value={m.key}>
                    {m.label}
                  </option>
                ))}
            </SelectField>
            <SettingsFields
              fields={auth.settings_fields}
              values={authSettings}
              onChange={(key, value) => setAuthSettings((v) => ({ ...v, [key]: value }))}
              errors={errors}
            />
            {sentence && <p className="text-xs text-slate-500">{sentence}</p>}
          </section>
        )}

        {connector.settings_fields.length > 0 && (
          <section className="space-y-4">
            <h3 className="text-sm font-semibold text-slate-900">What to read</h3>
            <SettingsFields
              fields={connector.settings_fields}
              values={settings}
              onChange={(key, value) => setSettings((v) => ({ ...v, [key]: value }))}
              errors={errors}
            />
          </section>
        )}

        <label className="flex cursor-pointer items-start gap-3">
          <input
            type="checkbox"
            className="mt-0.5 size-4 accent-brand-600"
            checked={enabled}
            onChange={(e) => setEnabled(e.target.checked)}
          />
          <span className="text-sm">
            <span className="font-medium text-slate-900">Turned on</span>
            <span className="block text-xs text-slate-500">
              Only sources that are on can be fetched or receive imports.
            </span>
          </span>
        </label>
      </form>
    </Dialog>
  )
}
