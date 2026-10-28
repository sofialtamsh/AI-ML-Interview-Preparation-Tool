import { CircleCheck, CircleX, FileJson, GitCompareArrows, History, Mic, Play, Eye } from 'lucide-react'
import { useMemo, useState } from 'react'

import { Button } from '../../../components/ui/Button'
import { Dialog } from '../../../components/ui/Dialog'
import { Alert, Badge, Card, Skeleton } from '../../../components/ui/Feedback'
import { SelectField, TextAreaField, TextField } from '../../../components/ui/Field'
import { useToast } from '../../../components/ui/Toast'
import { SectionBody } from '../../../learn/sections'
import { errorMessage } from '../../../lib/api'
import { cn } from '../../../lib/cn'
import { diffLines } from '../../../lib/diff'
import { formatDateTime, timeAgo } from '../../../lib/format'
import { PYODIDE_RUNTIME, runPython } from '../../../lib/pyodide'
import type { ContentOverview, ContentComponent, TransitionAction, VersionDetail, VersionStatus, VersionSummary } from '../../../lib/types'
import { useCan } from '../../api'
import { adminMediaUrl, useNarrate, useRecordCodeCheck, useRestoreVersion, useSaveVersion, useTransition, useVersion } from '../../contentApi'
import { ORIGIN_LABELS, VersionStatusBadge, studentView } from './shared'

type ActionRule = {
  action: TransitionAction
  label: string
  from: VersionStatus[]
  needs: string[]
  variant: 'primary' | 'secondary' | 'danger' | 'glow'
  askNote?: boolean
}

// Mirrors TRANSITIONS in app/content/service.py; the server enforces it regardless.
const ACTIONS: ActionRule[] = [
  { action: 'submit', label: 'Submit for review', from: ['draft'], needs: ['content.generate', 'content.review'], variant: 'primary' },
  { action: 'approve', label: 'Approve', from: ['under_review'], needs: ['content.publish'], variant: 'primary' },
  { action: 'publish', label: 'Publish to students', from: ['approved'], needs: ['content.publish'], variant: 'glow' },
  { action: 'send_back', label: 'Send back to draft', from: ['under_review', 'approved'], needs: ['content.review'], variant: 'secondary', askNote: true },
  { action: 'unpublish', label: 'Unpublish', from: ['published'], needs: ['content.publish'], variant: 'secondary', askNote: true },
  { action: 'reject', label: 'Reject', from: ['draft', 'under_review', 'approved'], needs: ['content.review'], variant: 'secondary', askNote: true },
  { action: 'archive', label: 'Archive', from: ['draft', 'under_review', 'approved', 'rejected'], needs: ['content.publish'], variant: 'secondary' },
]

type View = 'preview' | 'json' | 'compare'

export function VersionPanel({
  topicId,
  component,
  versionId,
  versions,
  overview,
  onSelect,
}: {
  topicId: string
  component: ContentComponent
  versionId: string
  versions: VersionSummary[]
  overview: ContentOverview | undefined
  onSelect: (id: string) => void
}) {
  const version = useVersion(versionId)
  const [view, setView] = useState<View>('preview')
  const [editing, setEditing] = useState(false)

  if (version.isPending) return <Skeleton className="h-96 rounded-2xl" />
  if (version.isError) return <Alert>{errorMessage(version.error)}</Alert>
  const data = version.data
  const latest = versions[0]?.id === data.id

  return (
    <div className="min-w-0 space-y-4">
      <Card className="p-5">
        <VersionHeader version={data} />
        <VersionActions version={data} latest={latest} onEdit={() => setEditing(true)} onSelect={onSelect} />
      </Card>

      {component === 'python' && <CodeCheckPanel version={data} />}
      {component === 'video' && <NarrationPanel version={data} overview={overview} />}

      <Card className="overflow-hidden">
        <div className="flex flex-wrap gap-1 border-b border-slate-100 px-3 py-2" role="tablist" aria-label="View">
          {(
            [
              ['preview', 'Student preview', Eye],
              ['json', 'Content (JSON)', FileJson],
              ['compare', 'Compare versions', GitCompareArrows],
            ] as const
          ).map(([key, label, Icon]) => (
            <button
              key={key}
              type="button"
              role="tab"
              aria-selected={view === key}
              disabled={key === 'compare' && versions.length < 2}
              onClick={() => setView(key)}
              className={cn(
                'inline-flex items-center gap-1.5 rounded-lg px-3 py-1.5 text-sm font-medium transition disabled:opacity-40',
                view === key ? 'bg-slate-900 text-white' : 'text-slate-600 hover:bg-slate-100',
              )}
            >
              <Icon className="size-4" aria-hidden />
              {label}
            </button>
          ))}
        </div>
        <div className="p-4 sm:p-6">
          {view === 'preview' && (
            <div className="space-y-6">
              <SectionBody component={component} body={studentView(component, data.body, data.narration)} audioUrl={adminMediaUrl} />
              {component === 'interview' && <Provenance body={data.body} />}
            </div>
          )}
          {view === 'json' && (
            <pre className="max-h-[70vh] overflow-auto rounded-xl bg-slate-950 p-4 font-mono text-xs leading-relaxed text-slate-100">
              {JSON.stringify(data.body, null, 2)}
            </pre>
          )}
          {view === 'compare' && <Compare version={data} versions={versions} />}
        </div>
      </Card>

      {editing && <EditDialog topicId={topicId} component={component} version={data} onClose={() => setEditing(false)} onSaved={onSelect} />}
    </div>
  )
}

function VersionHeader({ version }: { version: VersionDetail }) {
  return (
    <div className="space-y-2">
      <div className="flex flex-wrap items-center gap-2">
        <h2 className="font-display text-xl font-bold text-slate-900">Version {version.number}</h2>
        <VersionStatusBadge status={version.status} />
        {version.published && <Badge tone="success">Live for students</Badge>}
        <Badge>{ORIGIN_LABELS[version.origin]}</Badge>
      </div>
      <p className="text-sm text-slate-600">
        {version.created_by ? `${version.created_by}, ` : ''}
        {formatDateTime(version.created_at)}
        {version.model && <> · model {version.model}</>}
      </p>
      {version.note && <p className="text-sm text-slate-700">{version.note}</p>}
      {version.review_note && (
        <p className="rounded-xl bg-amber-50 px-3 py-2 text-sm text-amber-900 ring-1 ring-amber-100">
          <span className="font-semibold">Review note{version.reviewed_by ? ` from ${version.reviewed_by}` : ''}:</span> {version.review_note}
        </p>
      )}
    </div>
  )
}

function VersionActions({ version, latest, onEdit, onSelect }: { version: VersionDetail; latest: boolean; onEdit: () => void; onSelect: (id: string) => void }) {
  const transition = useTransition()
  const restore = useRestoreVersion()
  const toast = useToast()
  const canEdit = useCan('content.generate', 'content.review')
  const permissions = {
    'content.generate': useCan('content.generate'),
    'content.review': useCan('content.review'),
    'content.publish': useCan('content.publish'),
  } as Record<string, boolean>
  const [asking, setAsking] = useState<ActionRule | null>(null)
  const [note, setNote] = useState('')

  const available = ACTIONS.filter((rule) => rule.from.includes(version.status) && rule.needs.some((p) => permissions[p]))
  const needsCheck = version.component === 'python' && version.status === 'approved' && !version.code_checks.some((c) => c.passed && c.current)

  const run = (rule: ActionRule, withNote?: string) =>
    transition.mutate(
      { versionId: version.id, action: rule.action, note: withNote },
      {
        onSuccess: () => {
          toast.success(`Version ${version.number}: ${rule.label.toLowerCase()} done`)
          setAsking(null)
          setNote('')
        },
        onError: (error) => toast.error(errorMessage(error)),
      },
    )

  return (
    <div className="mt-4 space-y-3">
      {needsCheck && (
        <Alert tone="info">Publishing a Python lab needs a passing code check of this exact version. Run it below.</Alert>
      )}
      <div className="flex flex-wrap gap-2">
        {available.map((rule) => (
          <Button
            key={rule.action}
            variant={rule.variant}
            size="sm"
            loading={transition.isPending && transition.variables?.action === rule.action}
            disabled={rule.action === 'publish' && needsCheck}
            onClick={() => (rule.askNote ? setAsking(rule) : run(rule))}
          >
            {rule.label}
          </Button>
        ))}
        {canEdit && (
          <Button size="sm" variant="secondary" icon={<FileJson className="size-4" />} onClick={onEdit}>
            Edit as new draft
          </Button>
        )}
        {canEdit && !latest && (
          <Button
            size="sm"
            variant="secondary"
            icon={<History className="size-4" />}
            loading={restore.isPending}
            onClick={() =>
              restore.mutate(version.id, {
                onSuccess: (created) => {
                  toast.success(`Restored as version ${created.number} (draft)`)
                  onSelect(created.id)
                },
                onError: (error) => toast.error(errorMessage(error)),
              })
            }
          >
            Restore as new draft
          </Button>
        )}
      </div>
      <Dialog
        open={!!asking}
        onClose={() => setAsking(null)}
        title={asking ? `${asking.label}: version ${version.number}` : ''}
        description="Add a note for whoever works on it next (optional)."
        footer={
          <>
            <Button variant="secondary" onClick={() => setAsking(null)}>
              Cancel
            </Button>
            <Button loading={transition.isPending} onClick={() => asking && run(asking, note.trim())}>
              {asking?.label}
            </Button>
          </>
        }
      >
        <TextAreaField label="Note" value={note} maxLength={1000} rows={3} onChange={(e) => setNote(e.target.value)} />
      </Dialog>
    </div>
  )
}

function CodeCheckPanel({ version }: { version: VersionDetail }) {
  const record = useRecordCodeCheck()
  const toast = useToast()
  const canCheck = useCan('content.review', 'content.publish')
  const [status, setStatus] = useState<string | null>(null)
  const body = version.body as { steps: { code: string }[]; packages: string[] }
  const program = body.steps.map((s) => s.code).join('\n\n')

  const check = async () => {
    setStatus('Loading Python…')
    const result = await runPython(program, body.packages, (s) => setStatus(s === 'loading' ? 'Loading Python…' : 'Running the lab…'))
    setStatus('Recording the result…')
    record.mutate(
      { versionId: version.id, output: result.output, error: result.error, duration_ms: result.durationMs, runtime: PYODIDE_RUNTIME },
      {
        onSuccess: (saved) => (saved.passed ? toast.success('Code check passed') : toast.error('Code check failed: see the output')),
        onError: (error) => toast.error(errorMessage(error)),
        onSettled: () => setStatus(null),
      },
    )
  }

  return (
    <Card className="p-5">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h3 className="font-semibold text-slate-900">Code check</h3>
          <p className="text-sm text-slate-600">Runs this version&apos;s exact program in your browser (Pyodide). The server compares the output with the expected output.</p>
        </div>
        {canCheck && (
          <Button icon={<Play className="size-4" />} loading={status !== null} onClick={check}>
            {status ?? 'Run code check'}
          </Button>
        )}
      </div>
      {version.code_checks.length > 0 && (
        <ul className="mt-4 space-y-2">
          {version.code_checks.slice(0, 3).map((c) => (
            <li key={c.id} className="rounded-xl bg-slate-50 p-3 ring-1 ring-slate-200/70">
              <p className="flex flex-wrap items-center gap-2 text-sm">
                {c.passed ? <CircleCheck className="size-4 text-emerald-600" aria-hidden /> : <CircleX className="size-4 text-rose-600" aria-hidden />}
                <span className="font-semibold">{c.passed ? 'Passed' : 'Failed'}</span>
                <span className="text-slate-500">
                  {timeAgo(c.created_at)} · {c.duration_ms} ms · {c.runtime}
                </span>
              </p>
              {!c.passed && (
                <details className="mt-2">
                  <summary className="cursor-pointer text-xs font-semibold text-slate-600">Output</summary>
                  <pre className="mt-1 max-h-60 overflow-auto rounded-lg bg-slate-950 p-3 font-mono text-xs whitespace-pre-wrap text-slate-100">
                    {c.error ? `${c.output}\n${c.error}` : c.output || '(no output)'}
                  </pre>
                </details>
              )}
            </li>
          ))}
        </ul>
      )}
    </Card>
  )
}

function NarrationPanel({ version, overview }: { version: VersionDetail; overview: ContentOverview | undefined }) {
  const narrate = useNarrate()
  const toast = useToast()
  const canGenerate = useCan('content.generate')
  const voices = overview?.narration_voices ?? []
  const [voice, setVoice] = useState(voices[0] ?? '')
  const scenes = (version.body as { scenes: { title: string }[] }).scenes
  const ready = canGenerate && overview?.ai_configured && voices.length > 0

  return (
    <Card className="p-5">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h3 className="flex items-center gap-1.5 font-semibold text-slate-900">
            <Mic className="size-4" aria-hidden /> Narration
          </h3>
          <p className="text-sm text-slate-600">
            {version.narration.length
              ? `${version.narration.length} of ${scenes.length} scenes narrated.`
              : 'No recorded narration yet. Students can still play it with captions or their device voice.'}
          </p>
        </div>
        {ready && (
          <div className="flex flex-wrap items-end gap-2">
            <div className="w-56">
              <SelectField label="Voice" value={voice} onChange={(e) => setVoice(e.target.value)}>
                {voices.map((v) => (
                  <option key={v} value={v}>
                    {v.split(':')[0]}
                  </option>
                ))}
              </SelectField>
            </div>
            <Button
              loading={narrate.isPending}
              onClick={() =>
                narrate.mutate(
                  { versionId: version.id, voice },
                  { onSuccess: () => toast.success('Narration started. Clips appear as each scene finishes.'), onError: (e) => toast.error(errorMessage(e)) },
                )
              }
            >
              {version.narration.length ? 'Narrate missing scenes' : 'Generate narration'}
            </Button>
          </div>
        )}
      </div>
      {version.narration.length > 0 && (
        <ul className="mt-4 grid gap-2 sm:grid-cols-2">
          {version.narration.map((clip) => (
            <li key={clip.id} className="rounded-xl bg-slate-50 p-3 ring-1 ring-slate-200/70">
              <p className="text-xs font-semibold text-slate-600">
                Scene {clip.position + 1}: {scenes[clip.position]?.title} · {Math.round(clip.size / 1024)} KB
              </p>
              <audio controls preload="none" src={adminMediaUrl(clip.id)} className="mt-1 w-full" />
            </li>
          ))}
        </ul>
      )}
    </Card>
  )
}

const ORIGIN_TEXT: Record<string, string> = {
  ai_generated: 'AI generated',
  admin_created: 'Written by an admin',
  actual_interview: 'Actual interview record',
  research_derived: 'Research-derived',
}

/** Where each interview question came from: admins only, never sent to students. */
function Provenance({ body }: { body: Record<string, unknown> }) {
  const questions = body.questions as { question: string; origin: string; source_ref: string | null; asked_for_role: string | null }[]
  return (
    <section className="rounded-2xl bg-slate-50 p-4 ring-1 ring-slate-200">
      <h3 className="font-semibold text-slate-900">Provenance (admins only)</h3>
      <p className="text-xs text-slate-500">Students see only the label: Practice question, Asked in real interviews, or In demand right now.</p>
      <div className="mt-3 overflow-x-auto">
        <table className="w-full min-w-[36rem] text-left text-sm">
          <thead className="text-xs text-slate-500">
            <tr>
              <th className="py-1.5 pr-3 font-medium">Question</th>
              <th className="py-1.5 pr-3 font-medium">Origin</th>
              <th className="py-1.5 pr-3 font-medium">Record</th>
              <th className="py-1.5 font-medium">Role</th>
            </tr>
          </thead>
          <tbody>
            {questions.map((q, i) => (
              <tr key={i} className="border-t border-slate-200/70 align-top">
                <td className="py-1.5 pr-3">{q.question}</td>
                <td className="py-1.5 pr-3 whitespace-nowrap">{ORIGIN_TEXT[q.origin] ?? q.origin}</td>
                <td className="py-1.5 pr-3 font-mono text-xs">{q.source_ref ?? '—'}</td>
                <td className="py-1.5">{q.asked_for_role ?? '—'}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  )
}

function Compare({ version, versions }: { version: VersionDetail; versions: VersionSummary[] }) {
  const others = versions.filter((v) => v.id !== version.id)
  const [otherId, setOtherId] = useState(others[0]?.id ?? '')
  const other = useVersion(otherId || null)
  const lines = useMemo(
    () => (other.data ? diffLines(JSON.stringify(other.data.body, null, 2), JSON.stringify(version.body, null, 2)) : []),
    [other.data, version.body],
  )
  const changed = lines.filter((l) => l.kind !== 'same').length

  return (
    <div className="space-y-3">
      <div className="flex flex-wrap items-end gap-3">
        <div className="w-60">
          <SelectField label="Compare with" value={otherId} onChange={(e) => setOtherId(e.target.value)}>
            {others.map((v) => (
              <option key={v.id} value={v.id}>
                Version {v.number} ({v.status.replace('_', ' ')})
              </option>
            ))}
          </SelectField>
        </div>
        {other.data && (
          <p className="pb-2 text-sm text-slate-600">
            {changed ? `${changed} changed line(s): red is version ${other.data.number}, green is version ${version.number}.` : 'No differences.'}
          </p>
        )}
      </div>
      {other.isPending && otherId && <Skeleton className="h-64" />}
      {other.data && (
        <pre className="max-h-[70vh] overflow-auto rounded-xl bg-white p-3 font-mono text-xs leading-relaxed ring-1 ring-slate-200">
          {lines.map((line, i) => (
            <div
              key={i}
              className={cn(
                'px-2 whitespace-pre-wrap',
                line.kind === 'added' && 'bg-emerald-50 text-emerald-900',
                line.kind === 'removed' && 'bg-rose-50 text-rose-900 line-through decoration-rose-300',
                line.kind === 'same' && 'text-slate-500',
              )}
            >
              {line.kind === 'added' ? '+ ' : line.kind === 'removed' ? '− ' : '  '}
              {line.text}
            </div>
          ))}
        </pre>
      )}
    </div>
  )
}

function EditDialog({
  topicId,
  component,
  version,
  onClose,
  onSaved,
}: {
  topicId: string
  component: ContentComponent
  version: VersionDetail
  onClose: () => void
  onSaved: (id: string) => void
}) {
  const save = useSaveVersion(topicId, component)
  const toast = useToast()
  const [text, setText] = useState(() => JSON.stringify(version.body, null, 2))
  const [note, setNote] = useState('')
  const [problem, setProblem] = useState<string | null>(null)

  const submit = () => {
    let body: unknown
    try {
      body = JSON.parse(text)
    } catch (error) {
      setProblem(`That isn't valid JSON: ${(error as Error).message}`)
      return
    }
    setProblem(null)
    save.mutate(
      { body, based_on_id: version.id, note: note.trim() },
      {
        onSuccess: (created) => {
          toast.success(`Saved as version ${created.number} (draft)`)
          onSaved(created.id)
          onClose()
        },
        onError: (error) => setProblem(errorMessage(error)),
      },
    )
  }

  return (
    <Dialog
      open
      onClose={onClose}
      size="lg"
      title={`Edit version ${version.number}`}
      description="Saving creates a new draft; this version stays exactly as it is."
      footer={
        <>
          <Button variant="secondary" onClick={onClose}>
            Cancel
          </Button>
          <Button loading={save.isPending} onClick={submit}>
            Save as new draft
          </Button>
        </>
      }
    >
      <div className="space-y-3">
        {problem && <Alert>{problem}</Alert>}
        <label className="block">
          <span className="text-sm font-medium text-slate-800">Content (JSON)</span>
          <textarea
            value={text}
            onChange={(e) => setText(e.target.value)}
            spellCheck={false}
            rows={18}
            className="mt-1.5 block w-full rounded-xl bg-slate-950 p-3 font-mono text-xs leading-relaxed text-slate-100 outline-none focus:ring-2 focus:ring-brand-500"
          />
        </label>
        <TextField label="What changed? (optional)" value={note} maxLength={500} onChange={(e) => setNote(e.target.value)} />
        {version.component === 'python' && (
          <p className="text-xs text-slate-500">Changing the code needs a new code check before publishing.</p>
        )}
      </div>
    </Dialog>
  )
}
