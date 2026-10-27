import { Lock, Pencil, Plus, Trash2, Users } from 'lucide-react'
import { useState, type FormEvent } from 'react'

import { Button } from '../../../components/ui/Button'
import { Dialog } from '../../../components/ui/Dialog'
import { Alert, Badge, Card, Skeleton } from '../../../components/ui/Feedback'
import { TextField } from '../../../components/ui/Field'
import { useToast } from '../../../components/ui/Toast'
import { errorMessage } from '../../../lib/api'
import type { PermissionInfo, Role } from '../../../lib/types'
import { useCan, useDeleteRole, usePermissions, useRoles, useSaveRole } from '../../api'

const GROUPS: { label: string; prefixes: string[] }[] = [
  { label: 'Platform', prefixes: ['admins.', 'roles.', 'audit.', 'settings.'] },
  { label: 'Interview sources', prefixes: ['sources.'] },
  { label: 'Agents & intelligence', prefixes: ['agents.', 'intelligence.'] },
  { label: 'Curriculum & content', prefixes: ['taxonomy.', 'content.'] },
  { label: 'Students & analytics', prefixes: ['students.', 'analytics.', 'rankings.'] },
]

function groupOf(key: string) {
  return GROUPS.find((g) => g.prefixes.some((p) => key.startsWith(p)))?.label ?? 'Other'
}

function RoleDialog({
  role,
  permissions,
  onClose,
}: {
  role: Role | null
  permissions: PermissionInfo[]
  onClose: () => void
}) {
  const [name, setName] = useState(role?.name ?? '')
  const [description, setDescription] = useState(role?.description ?? '')
  const [selected, setSelected] = useState<string[]>(role?.permissions ?? [])
  const save = useSaveRole()
  const toast = useToast()

  const toggle = (key: string, on: boolean) =>
    setSelected((current) => (on ? [...current, key] : current.filter((k) => k !== key)))

  const submit = (event: FormEvent) => {
    event.preventDefault()
    save.mutate(
      { id: role?.id, name: name.trim(), description: description.trim(), permissions: selected },
      {
        onSuccess: (saved) => {
          toast.success(role ? `Saved ${saved.name}` : `Created ${saved.name}`)
          onClose()
        },
      },
    )
  }

  return (
    <Dialog
      open
      onClose={onClose}
      size="lg"
      title={role ? `Edit ${role.name}` : 'New custom role'}
      description="Admins with this role get exactly the permissions you tick."
      footer={
        <>
          <Button variant="secondary" onClick={onClose}>
            Cancel
          </Button>
          <Button
            type="submit"
            form="role-form"
            loading={save.isPending}
            disabled={name.trim().length < 2 || selected.length === 0}
          >
            {role ? 'Save role' : 'Create role'}
          </Button>
        </>
      }
    >
      <form id="role-form" onSubmit={submit} className="space-y-5">
        {save.isError && <Alert>{errorMessage(save.error)}</Alert>}
        <TextField label="Role name" value={name} onChange={(e) => setName(e.target.value)} />
        <TextField
          label="Description"
          value={description}
          onChange={(e) => setDescription(e.target.value)}
          placeholder="What is this role for?"
        />
        {GROUPS.map((group) => {
          const items = permissions.filter((p) => groupOf(p.key) === group.label)
          return (
            <fieldset key={group.label}>
              <legend className="mb-2 text-xs font-semibold tracking-wide text-slate-500 uppercase">
                {group.label}
              </legend>
              <div className="grid gap-2 sm:grid-cols-2">
                {items.map((p) => (
                  <label
                    key={p.key}
                    className="flex cursor-pointer gap-3 rounded-xl p-3 ring-1 ring-slate-200 transition has-[:checked]:bg-brand-50/60 has-[:checked]:ring-brand-300"
                  >
                    <input
                      type="checkbox"
                      className="mt-0.5 size-4 accent-brand-600"
                      checked={selected.includes(p.key)}
                      onChange={(e) => toggle(p.key, e.target.checked)}
                    />
                    <span>
                      <span className="block font-mono text-xs font-medium text-slate-900">{p.key}</span>
                      <span className="block text-xs text-slate-500">{p.description}</span>
                    </span>
                  </label>
                ))}
              </div>
            </fieldset>
          )
        })}
      </form>
    </Dialog>
  )
}

export default function RolesTab() {
  const roles = useRoles()
  const permissions = usePermissions()
  const canEdit = useCan('roles.manage')
  const remove = useDeleteRole()
  const toast = useToast()
  const [editing, setEditing] = useState<Role | null | 'new'>(null)
  const [deleting, setDeleting] = useState<Role | null>(null)

  if (roles.isPending || permissions.isPending) {
    return (
      <div className="grid gap-4 md:grid-cols-2">
        {[0, 1, 2, 3].map((i) => (
          <Skeleton key={i} className="h-40 rounded-2xl" />
        ))}
      </div>
    )
  }
  if (roles.isError || permissions.isError) {
    return <Alert>{errorMessage(roles.error ?? permissions.error)}</Alert>
  }

  return (
    <div>
      <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
        <p className="max-w-2xl text-sm text-slate-600">
          System roles are defined by the platform and can't be changed. Create a custom role when
          someone needs a different combination of permissions.
        </p>
        {canEdit && (
          <Button icon={<Plus className="size-4" />} onClick={() => setEditing('new')}>
            New role
          </Button>
        )}
      </div>
      <div className="grid gap-4 md:grid-cols-2">
        {roles.data.map((role) => (
          <Card key={role.id} className="flex flex-col p-5">
            <div className="flex items-start justify-between gap-3">
              <div>
                <h3 className="flex items-center gap-2 font-display font-semibold text-slate-900">
                  {role.name}
                  {role.is_system ? (
                    <Badge>
                      <Lock className="size-3" aria-hidden /> System
                    </Badge>
                  ) : (
                    <Badge tone="brand">Custom</Badge>
                  )}
                </h3>
                <p className="mt-1 text-sm text-slate-500">{role.description || 'No description'}</p>
              </div>
              <span className="flex items-center gap-1 text-xs whitespace-nowrap text-slate-500">
                <Users className="size-3.5" aria-hidden /> {role.admin_count}
              </span>
            </div>
            <div className="mt-4 flex flex-wrap gap-1.5">
              {role.permissions.map((key) => (
                <span
                  key={key}
                  className="rounded-md bg-slate-100 px-1.5 py-0.5 font-mono text-[11px] text-slate-700"
                >
                  {key}
                </span>
              ))}
            </div>
            {canEdit && !role.is_system && (
              <div className="mt-4 flex gap-2 border-t border-slate-100 pt-4">
                <Button variant="secondary" size="sm" icon={<Pencil className="size-3.5" />} onClick={() => setEditing(role)}>
                  Edit
                </Button>
                <Button variant="ghost" size="sm" icon={<Trash2 className="size-3.5" />} onClick={() => setDeleting(role)}>
                  Delete
                </Button>
              </div>
            )}
          </Card>
        ))}
      </div>

      {editing && (
        <RoleDialog
          key={editing === 'new' ? 'new' : editing.id}
          role={editing === 'new' ? null : editing}
          permissions={permissions.data}
          onClose={() => setEditing(null)}
        />
      )}
      <Dialog
        open={!!deleting}
        onClose={() => {
          setDeleting(null)
          remove.reset()
        }}
        title={`Delete ${deleting?.name ?? 'role'}?`}
        footer={
          <>
            <Button variant="secondary" onClick={() => setDeleting(null)}>
              Cancel
            </Button>
            <Button
              variant="danger"
              loading={remove.isPending}
              onClick={() =>
                deleting &&
                remove.mutate(deleting.id, {
                  onSuccess: () => {
                    toast.success(`Deleted ${deleting.name}`)
                    setDeleting(null)
                  },
                })
              }
            >
              Delete role
            </Button>
          </>
        }
      >
        {remove.isError ? (
          <Alert>{errorMessage(remove.error)}</Alert>
        ) : (
          <p className="text-sm text-slate-600">
            This can't be undone. Roles that are still assigned to an admin can't be deleted.
          </p>
        )}
      </Dialog>
    </div>
  )
}
