import { Archive, ArchiveRestore, FolderPlus, Pencil, Plus } from 'lucide-react'
import { useState } from 'react'
import { Link } from 'react-router'

import { Button } from '../../../components/ui/Button'
import { Dialog } from '../../../components/ui/Dialog'
import { Alert, Badge, Card, PageHeader, Skeleton } from '../../../components/ui/Feedback'
import { TextAreaField, TextField } from '../../../components/ui/Field'
import { useToast } from '../../../components/ui/Toast'
import { errorMessage } from '../../../lib/api'
import { cn } from '../../../lib/cn'
import type { TaxonomyDomain, TaxonomyTopic } from '../../../lib/types'
import { Toggle } from '../../../learn/widgets/controls'
import { useCan } from '../../api'
import { useCreateDomain, useCreateTopic, useTaxonomyAdmin, useUpdateDomain, useUpdateTopic } from '../../contentApi'

type Editing =
  | { kind: 'new-domain' }
  | { kind: 'domain'; domain: TaxonomyDomain }
  | { kind: 'new-topic'; domain: TaxonomyDomain }
  | { kind: 'topic'; topic: TaxonomyTopic }

export default function TopicsPage() {
  const taxonomy = useTaxonomyAdmin()
  const canManage = useCan('taxonomy.manage')
  const canContent = useCan('content.generate', 'content.review', 'content.publish')
  const [showArchived, setShowArchived] = useState(false)
  const [editing, setEditing] = useState<Editing | null>(null)

  const domains = (taxonomy.data ?? []).filter((d) => showArchived || !d.archived)
  const archivedCount = (taxonomy.data ?? []).reduce((n, d) => n + (d.archived ? 1 : 0) + d.topics.filter((t) => t.archived).length, 0)

  return (
    <div className="space-y-6">
      <PageHeader
        title="Domains & topics"
        description="The curriculum map that agents, research and content all use. Items are archived, never deleted."
        actions={
          canManage && (
            <Button icon={<FolderPlus className="size-4" />} onClick={() => setEditing({ kind: 'new-domain' })}>
              Add domain
            </Button>
          )
        }
      />
      {archivedCount > 0 && (
        <div className="max-w-xs">
          <Toggle label={`Show archived (${archivedCount})`} checked={showArchived} onChange={setShowArchived} />
        </div>
      )}
      {taxonomy.isPending && <Skeleton className="h-64 rounded-2xl" />}
      {taxonomy.isError && <Alert>{errorMessage(taxonomy.error)}</Alert>}

      {domains.map((domain) => (
        <Card key={domain.id} className={cn('overflow-hidden', domain.archived && 'opacity-70')}>
          <div className="flex flex-wrap items-start justify-between gap-3 border-b border-slate-100 px-5 py-4">
            <div className="min-w-0">
              <h2 className="flex flex-wrap items-center gap-2 font-display text-base font-semibold text-slate-900">
                {domain.name}
                {domain.archived && <Badge>Archived</Badge>}
              </h2>
              {domain.description && <p className="mt-0.5 text-sm text-slate-500">{domain.description}</p>}
            </div>
            {canManage && (
              <div className="flex flex-wrap gap-1">
                {!domain.archived && (
                  <Button size="sm" variant="ghost" icon={<Plus className="size-4" />} onClick={() => setEditing({ kind: 'new-topic', domain })}>
                    Add topic
                  </Button>
                )}
                <Button size="sm" variant="ghost" icon={<Pencil className="size-4" />} onClick={() => setEditing({ kind: 'domain', domain })}>
                  Edit
                </Button>
                <ArchiveDomain domain={domain} />
              </div>
            )}
          </div>
          <ul className="divide-y divide-slate-100">
            {domain.topics
              .filter((t) => showArchived || !t.archived)
              .map((topic) => (
                <TopicRow key={topic.id} topic={topic} canManage={canManage} canContent={canContent} onEdit={() => setEditing({ kind: 'topic', topic })} />
              ))}
            {domain.topics.filter((t) => showArchived || !t.archived).length === 0 && (
              <li className="px-5 py-4 text-sm text-slate-500">No topics yet.</li>
            )}
          </ul>
        </Card>
      ))}

      {editing && <EditDialog editing={editing} onClose={() => setEditing(null)} />}
    </div>
  )
}

function ArchiveDomain({ domain }: { domain: TaxonomyDomain }) {
  const update = useUpdateDomain()
  const toast = useToast()
  return (
    <Button
      size="sm"
      variant="ghost"
      loading={update.isPending}
      icon={domain.archived ? <ArchiveRestore className="size-4" /> : <Archive className="size-4" />}
      onClick={() =>
        update.mutate(
          { id: domain.id, archived: !domain.archived },
          {
            onSuccess: () => toast.success(domain.archived ? `${domain.name} restored` : `${domain.name} archived`),
            onError: (e) => toast.error(errorMessage(e)),
          },
        )
      }
    >
      {domain.archived ? 'Restore' : 'Archive'}
    </Button>
  )
}

function TopicRow({ topic, canManage, canContent, onEdit }: { topic: TaxonomyTopic; canManage: boolean; canContent: boolean; onEdit: () => void }) {
  const update = useUpdateTopic()
  const toast = useToast()
  const canPilot = useCan('settings.manage') && canManage

  const change = (body: { archived?: boolean; is_pilot?: boolean }, done: string) =>
    update.mutate({ id: topic.id, ...body }, { onSuccess: () => toast.success(done), onError: (e) => toast.error(errorMessage(e)) })

  return (
    <li className={cn('flex flex-wrap items-center gap-x-4 gap-y-2 px-5 py-3', topic.archived && 'opacity-60')}>
      <div className="min-w-0 flex-1">
        <p className="flex flex-wrap items-center gap-2 font-medium text-slate-900">
          {canContent && !topic.archived ? (
            <Link to={`/admin/content/${topic.id}`} className="hover:text-brand-700 hover:underline">
              {topic.name}
            </Link>
          ) : (
            topic.name
          )}
          {topic.is_pilot && <Badge tone="brand">Pilot</Badge>}
          {topic.published_components > 0 && <Badge tone="success">{topic.published_components} live</Badge>}
          {topic.archived && <Badge>Archived</Badge>}
        </p>
        <p className="font-mono text-xs text-slate-500">{topic.slug}</p>
      </div>
      <div className="flex flex-wrap items-center gap-1">
        {canPilot && !topic.archived && (
          <label className="mr-2 inline-flex items-center gap-2 text-xs font-medium text-slate-600">
            <input
              type="checkbox"
              className="accent-brand-600"
              checked={topic.is_pilot}
              disabled={update.isPending}
              onChange={(e) => change({ is_pilot: e.target.checked }, e.target.checked ? `${topic.name} is now a pilot topic` : `${topic.name} left the pilot`)}
            />
            Pilot
          </label>
        )}
        {canManage && (
          <>
            <Button size="sm" variant="ghost" icon={<Pencil className="size-4" />} onClick={onEdit}>
              Edit
            </Button>
            <Button
              size="sm"
              variant="ghost"
              icon={topic.archived ? <ArchiveRestore className="size-4" /> : <Archive className="size-4" />}
              onClick={() => change({ archived: !topic.archived }, topic.archived ? `${topic.name} restored` : `${topic.name} archived`)}
            >
              {topic.archived ? 'Restore' : 'Archive'}
            </Button>
          </>
        )}
      </div>
    </li>
  )
}

function EditDialog({ editing, onClose }: { editing: Editing; onClose: () => void }) {
  const createDomain = useCreateDomain()
  const updateDomain = useUpdateDomain()
  const createTopic = useCreateTopic()
  const updateTopic = useUpdateTopic()
  const toast = useToast()
  const start =
    editing.kind === 'domain' ? editing.domain : editing.kind === 'topic' ? editing.topic : { name: '', description: '' }
  const [name, setName] = useState(start.name)
  const [description, setDescription] = useState(start.description)
  const [error, setError] = useState<string | null>(null)
  const pending = createDomain.isPending || updateDomain.isPending || createTopic.isPending || updateTopic.isPending

  const title = {
    'new-domain': 'Add a domain',
    domain: 'Edit domain',
    'new-topic': editing.kind === 'new-topic' ? `Add a topic to ${editing.domain.name}` : '',
    topic: 'Edit topic',
  }[editing.kind]

  const done = (message: string) => ({
    onSuccess: () => {
      toast.success(message)
      onClose()
    },
    onError: (e: unknown) => setError(errorMessage(e)),
  })

  const submit = () => {
    const body = { name: name.trim(), description: description.trim() }
    if (body.name.length < 2) {
      setError('Name needs at least 2 characters.')
      return
    }
    setError(null)
    if (editing.kind === 'new-domain') createDomain.mutate(body, done(`${body.name} added`))
    if (editing.kind === 'domain') updateDomain.mutate({ id: editing.domain.id, ...body }, done('Domain saved'))
    if (editing.kind === 'new-topic') createTopic.mutate({ domain_id: editing.domain.id, ...body }, done(`${body.name} added`))
    if (editing.kind === 'topic') updateTopic.mutate({ id: editing.topic.id, ...body }, done('Topic saved'))
  }

  return (
    <Dialog
      open
      onClose={onClose}
      title={title}
      description={editing.kind === 'topic' ? 'Renaming keeps the topic’s link (slug) and all its content.' : undefined}
      footer={
        <>
          <Button variant="secondary" onClick={onClose}>
            Cancel
          </Button>
          <Button loading={pending} onClick={submit}>
            Save
          </Button>
        </>
      }
    >
      <div className="space-y-4">
        {error && <Alert>{error}</Alert>}
        <TextField label="Name" value={name} maxLength={200} onChange={(e) => setName(e.target.value)} autoFocus />
        <TextAreaField label="Description (optional)" value={description} maxLength={1000} rows={3} onChange={(e) => setDescription(e.target.value)} />
      </div>
    </Dialog>
  )
}
