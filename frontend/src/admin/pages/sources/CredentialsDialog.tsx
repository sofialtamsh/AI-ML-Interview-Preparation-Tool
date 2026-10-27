import { LockKeyhole } from 'lucide-react'
import { useState, type FormEvent } from 'react'

import { Button } from '../../../components/ui/Button'
import { Dialog } from '../../../components/ui/Dialog'
import { Alert } from '../../../components/ui/Feedback'
import { PasswordField, TextField } from '../../../components/ui/Field'
import { useToast } from '../../../components/ui/Toast'
import { errorMessage } from '../../../lib/api'
import type { SourceCatalog, SourceDetail } from '../../../lib/types'
import { useClearCredentials, useSetCredentials } from '../../api'

/** Write-only: stored values are never sent back, so the inputs always start empty. */
export function CredentialsDialog({
  catalog,
  source,
  onClose,
}: {
  catalog: SourceCatalog
  source: SourceDetail
  onClose: () => void
}) {
  const fields = catalog.auth_methods.find((m) => m.key === source.auth_method)?.secret_fields ?? []
  const stored = new Set(source.credentials.stored)
  const [values, setValues] = useState<Record<string, string>>(
    Object.fromEntries(fields.map((f) => [f.key, ''])),
  )
  const save = useSetCredentials(source.id)
  const clear = useClearCredentials(source.id)
  const toast = useToast()
  const [confirmClear, setConfirmClear] = useState(false)

  const ready = fields.every((f) => values[f.key] || stored.has(f.key))
  const changed = fields.some((f) => values[f.key])

  const submit = (event: FormEvent) => {
    event.preventDefault()
    save.mutate(values, {
      onSuccess: () => {
        toast.success('Credentials saved. Test the connection to check them.')
        onClose()
      },
    })
  }

  return (
    <Dialog
      open
      onClose={onClose}
      title={`Credentials for ${source.name}`}
      description="Stored encrypted. Once saved, nobody can view them again, including you."
      footer={
        <>
          {source.credentials.stored.length > 0 && (
            <Button
              variant="ghost"
              className="mr-auto text-rose-700 hover:bg-rose-50"
              loading={clear.isPending}
              onClick={() =>
                confirmClear
                  ? clear.mutate(undefined, {
                      onSuccess: () => {
                        toast.success('Stored credentials deleted')
                        onClose()
                      },
                    })
                  : setConfirmClear(true)
              }
            >
              {confirmClear ? 'Click again to delete' : 'Delete stored'}
            </Button>
          )}
          <Button variant="secondary" onClick={onClose}>
            Cancel
          </Button>
          <Button
            type="submit"
            form="credentials-form"
            loading={save.isPending}
            disabled={!catalog.credential_storage_ready || !ready || !changed}
          >
            Save credentials
          </Button>
        </>
      }
    >
      <form id="credentials-form" onSubmit={submit} className="space-y-4" autoComplete="off">
        {!catalog.credential_storage_ready && (
          <Alert>
            Credential storage isn't set up on the server (IPP_CREDENTIALS_KEYS is missing), so
            credentials can't be saved yet.
          </Alert>
        )}
        {(save.isError || clear.isError) && <Alert>{errorMessage(save.error ?? clear.error)}</Alert>}
        <div className="flex gap-2.5 rounded-xl bg-slate-50 p-3 text-xs text-slate-600 ring-1 ring-slate-200">
          <LockKeyhole className="mt-0.5 size-4 shrink-0 text-slate-500" aria-hidden />
          <p>
            They're only used by the server to sign in to {source.base_url ?? 'this source'}, and
            never appear in pages, logs, reports or anything students can see.
          </p>
        </div>
        {fields.map((field) => {
          const common = {
            label: field.label,
            value: values[field.key],
            onChange: (e: { target: { value: string } }) =>
              setValues((v) => ({ ...v, [field.key]: e.target.value })),
            placeholder: stored.has(field.key) ? 'Saved · leave blank to keep' : '',
            autoComplete: 'off',
            spellCheck: false,
          }
          return field.kind === 'password' ? (
            <PasswordField key={field.key} {...common} autoComplete="new-password" />
          ) : (
            <TextField key={field.key} {...common} />
          )
        })}
      </form>
    </Dialog>
  )
}
