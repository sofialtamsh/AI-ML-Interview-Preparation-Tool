import { Copy, KeyRound, Pencil, UserPlus, Wand2 } from 'lucide-react'
import { useState, type FormEvent } from 'react'

import { Button } from '../../../components/ui/Button'
import { Dialog } from '../../../components/ui/Dialog'
import { Alert, Badge, Card, Skeleton } from '../../../components/ui/Feedback'
import { SelectField, TextField } from '../../../components/ui/Field'
import { useToast } from '../../../components/ui/Toast'
import { errorMessage } from '../../../lib/api'
import { timeAgo } from '../../../lib/format'
import { generateTemporaryPassword, PASSWORD_MIN_LENGTH } from '../../../lib/password'
import type { AdminStatus, AdminUser, Role } from '../../../lib/types'
import { useAdminUsers, useCurrentAdmin, useRoles, useSaveAdminUser } from '../../api'
import { StatusBadge } from '../../StatusBadge'

function TemporaryPasswordInput({
  value,
  onChange,
  label,
  hint,
}: {
  value: string
  onChange: (value: string) => void
  label: string
  hint: string
}) {
  const toast = useToast()
  return (
    <div>
      <TextField
        label={label}
        value={value}
        onChange={(e) => onChange(e.target.value)}
        autoComplete="new-password"
        className="font-mono"
        hint={hint}
        labelAction={
          <span className="flex gap-1">
            <button
              type="button"
              onClick={() => onChange(generateTemporaryPassword())}
              className="inline-flex items-center gap-1 rounded-md px-1.5 py-0.5 text-xs font-semibold text-brand-700 hover:bg-brand-50"
            >
              <Wand2 className="size-3.5" aria-hidden /> Generate
            </button>
            {value && (
              <button
                type="button"
                onClick={() =>
                  navigator.clipboard
                    .writeText(value)
                    .then(() => toast.success('Password copied'))
                    .catch(() => toast.error('Could not copy'))
                }
                className="inline-flex items-center gap-1 rounded-md px-1.5 py-0.5 text-xs font-semibold text-slate-600 hover:bg-slate-100"
              >
                <Copy className="size-3.5" aria-hidden /> Copy
              </button>
            )}
          </span>
        }
      />
    </div>
  )
}

function RolePicker({
  roles,
  selected,
  onChange,
}: {
  roles: Role[]
  selected: string[]
  onChange: (ids: string[]) => void
}) {
  return (
    <fieldset>
      <legend className="mb-2 text-sm font-medium text-slate-800">Roles</legend>
      <div className="space-y-2">
        {roles.map((role) => (
          <label
            key={role.id}
            className="flex cursor-pointer gap-3 rounded-xl p-3 ring-1 ring-slate-200 transition has-[:checked]:bg-brand-50/60 has-[:checked]:ring-brand-300"
          >
            <input
              type="checkbox"
              className="mt-0.5 size-4 accent-brand-600"
              checked={selected.includes(role.id)}
              onChange={(e) =>
                onChange(
                  e.target.checked ? [...selected, role.id] : selected.filter((id) => id !== role.id),
                )
              }
            />
            <span>
              <span className="block text-sm font-medium text-slate-900">{role.name}</span>
              <span className="block text-xs text-slate-500">{role.description}</span>
            </span>
          </label>
        ))}
      </div>
    </fieldset>
  )
}

function AdminDialog({
  admin,
  roles,
  open,
  onClose,
}: {
  admin: AdminUser | null
  roles: Role[]
  open: boolean
  onClose: () => void
}) {
  const me = useCurrentAdmin()
  const isSelf = admin?.id === me.id
  const [email, setEmail] = useState(admin?.email ?? '')
  const [fullName, setFullName] = useState(admin?.full_name ?? '')
  const [roleIds, setRoleIds] = useState<string[]>(admin?.roles.map((r) => r.id) ?? [])
  const [status, setStatus] = useState<AdminStatus>(admin?.status ?? 'active')
  const [password, setPassword] = useState(admin ? '' : generateTemporaryPassword())
  const save = useSaveAdminUser()
  const toast = useToast()

  const submit = (event: FormEvent) => {
    event.preventDefault()
    const body = admin
      ? {
          id: admin.id,
          full_name: fullName.trim(),
          role_ids: roleIds,
          ...(isSelf ? {} : { status }),
          ...(password ? { temporary_password: password } : {}),
        }
      : { email, full_name: fullName.trim(), role_ids: roleIds, temporary_password: password }
    save.mutate(body, {
      onSuccess: (saved) => {
        toast.success(admin ? `Saved ${saved.full_name}` : `${saved.full_name} can now sign in`)
        onClose()
      },
    })
  }

  const valid =
    fullName.trim().length >= 2 &&
    roleIds.length > 0 &&
    (admin ? !password || password.length >= PASSWORD_MIN_LENGTH : email.includes('@') && password.length >= PASSWORD_MIN_LENGTH)

  return (
    <Dialog
      open={open}
      onClose={onClose}
      size="lg"
      title={admin ? `Edit ${admin.full_name}` : 'Add an admin'}
      description={
        admin
          ? 'Changes take effect on their next request.'
          : "They'll sign in with the temporary password and must choose their own."
      }
      footer={
        <>
          <Button variant="secondary" onClick={onClose}>
            Cancel
          </Button>
          <Button type="submit" form="admin-form" loading={save.isPending} disabled={!valid}>
            {admin ? 'Save changes' : 'Add admin'}
          </Button>
        </>
      }
    >
      <form id="admin-form" onSubmit={submit} className="space-y-5">
        {save.isError && <Alert>{errorMessage(save.error)}</Alert>}
        <div className="grid gap-4 sm:grid-cols-2">
          <TextField
            label="Full name"
            value={fullName}
            onChange={(e) => setFullName(e.target.value)}
          />
          <TextField
            label="Work email"
            type="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            disabled={!!admin}
          />
        </div>
        {admin && !isSelf && (
          <SelectField
            label="Status"
            value={status}
            onChange={(e) => setStatus(e.target.value as AdminStatus)}
            hint={status === 'disabled' ? 'Disabling signs them out everywhere immediately.' : undefined}
          >
            <option value="active">Active</option>
            <option value="disabled">Disabled</option>
          </SelectField>
        )}
        <RolePicker roles={roles} selected={roleIds} onChange={setRoleIds} />
        {(!admin || !isSelf) && (
          <TemporaryPasswordInput
            label={admin ? 'Reset password (optional)' : 'Temporary password'}
            value={password}
            onChange={setPassword}
            hint={
              admin
                ? 'Setting one signs them out and makes them choose a new password at next sign-in.'
                : 'Share it with them securely. It works until they set their own.'
            }
          />
        )}
      </form>
    </Dialog>
  )
}

export default function AdminsTab() {
  const me = useCurrentAdmin()
  const admins = useAdminUsers()
  const roles = useRoles()
  const [editing, setEditing] = useState<AdminUser | null | 'new'>(null)

  return (
    <Card className="overflow-hidden">
      <div className="flex flex-wrap items-center justify-between gap-3 border-b border-slate-100 px-5 py-4">
        <div>
          <h2 className="font-display text-base font-semibold text-slate-900">Admins</h2>
          <p className="text-sm text-slate-500">People who can sign in to this console.</p>
        </div>
        <Button icon={<UserPlus className="size-4" />} onClick={() => setEditing('new')} disabled={!roles.data}>
          Add admin
        </Button>
      </div>
      {admins.isPending ? (
        <div className="space-y-3 p-5">
          <Skeleton className="h-12" />
          <Skeleton className="h-12" />
        </div>
      ) : admins.isError ? (
        <div className="p-5">
          <Alert>{errorMessage(admins.error)}</Alert>
        </div>
      ) : (
        <div className="overflow-x-auto">
          <table className="w-full min-w-[720px] text-left text-sm">
            <thead className="border-b border-slate-100 bg-slate-50/80 text-xs text-slate-500">
              <tr>
                <th className="px-5 py-3 font-medium">Admin</th>
                <th className="px-3 py-3 font-medium">Roles</th>
                <th className="px-3 py-3 font-medium">Status</th>
                <th className="px-3 py-3 font-medium">Last sign-in</th>
                <th className="px-5 py-3" />
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {admins.data.map((admin) => (
                <tr key={admin.id}>
                  <td className="px-5 py-3">
                    <p className="font-medium text-slate-900">
                      {admin.full_name}
                      {admin.id === me.id && <span className="ml-2 text-xs text-slate-400">(you)</span>}
                    </p>
                    <p className="text-xs text-slate-500">{admin.email}</p>
                  </td>
                  <td className="px-3 py-3">
                    <div className="flex flex-wrap gap-1">
                      {admin.roles.map((r) => (
                        <Badge key={r.id} tone="brand">
                          {r.name}
                        </Badge>
                      ))}
                    </div>
                  </td>
                  <td className="px-3 py-3">
                    <div className="flex flex-wrap items-center gap-1">
                      <StatusBadge status={admin.status} />
                      {admin.must_change_password && (
                        <Badge tone="warning">
                          <KeyRound className="size-3" aria-hidden /> Temporary password
                        </Badge>
                      )}
                    </div>
                  </td>
                  <td className="px-3 py-3 text-slate-600">{timeAgo(admin.last_login_at)}</td>
                  <td className="px-5 py-3 text-right">
                    <Button
                      variant="ghost"
                      size="sm"
                      icon={<Pencil className="size-3.5" />}
                      onClick={() => setEditing(admin)}
                      disabled={!roles.data}
                    >
                      Edit
                    </Button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
      {editing && roles.data && (
        <AdminDialog
          key={editing === 'new' ? 'new' : editing.id}
          admin={editing === 'new' ? null : editing}
          roles={roles.data}
          open
          onClose={() => setEditing(null)}
        />
      )}
    </Card>
  )
}
