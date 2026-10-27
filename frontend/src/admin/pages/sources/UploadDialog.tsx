import { CircleCheck, FileUp, TriangleAlert, X } from 'lucide-react'
import { useRef, useState, type DragEvent, type FormEvent } from 'react'

import { Button } from '../../../components/ui/Button'
import { Dialog } from '../../../components/ui/Dialog'
import { Spinner } from '../../../components/ui/Feedback'
import { TextField } from '../../../components/ui/Field'
import { errorMessage } from '../../../lib/api'
import { cn } from '../../../lib/cn'
import type { SourceCatalog, SourceDetail } from '../../../lib/types'
import { useUploadToSource } from '../../api'
import { runSummary } from './shared'

type Outcome = { name: string; state: 'waiting' | 'uploading' | 'done' | 'failed'; message?: string }

const TABULAR = /\.(csv|json|jsonl|ndjson)$/i

const KIND_NAMES: Record<string, string> = {
  '.csv': 'CSV',
  '.json': 'JSON',
  '.jsonl': 'JSON',
  '.ndjson': 'JSON',
  '.pdf': 'PDF',
  '.docx': 'Word (.docx)',
  '.txt': 'text',
  '.md': 'Markdown',
  '.markdown': 'Markdown',
  '.html': 'saved web pages',
  '.htm': 'saved web pages',
}

/** "CSV, JSON, PDF, Word (.docx), text, Markdown or saved web pages" */
export function describeFileTypes(extensions: string[]): string {
  const names = [...new Set(extensions.map((x) => KIND_NAMES[x] ?? x.slice(1).toUpperCase()))]
  return names.length > 1 ? `${names.slice(0, -1).join(', ')} or ${names.at(-1)}` : (names[0] ?? '')
}

export function UploadDialog({
  catalog,
  source,
  onClose,
}: {
  catalog: SourceCatalog
  source: SourceDetail
  onClose: () => void
}) {
  const input = useRef<HTMLInputElement>(null)
  const [files, setFiles] = useState<File[]>([])
  const [outcomes, setOutcomes] = useState<Outcome[]>([])
  const [idField, setIdField] = useState('')
  const [titleField, setTitleField] = useState('')
  const [dragging, setDragging] = useState(false)
  const upload = useUploadToSource(source.id)
  const maxBytes = catalog.max_upload_mb * 1024 * 1024
  const busy = outcomes.some((o) => o.state === 'uploading')
  const finished = outcomes.length > 0 && outcomes.every((o) => o.state === 'done' || o.state === 'failed')

  const add = (list: FileList | null) => {
    // Copy now: the input is cleared right after, which empties the live FileList.
    const picked = Array.from(list ?? [])
    if (!picked.length) return
    setOutcomes([])
    setFiles((current) => {
      const names = new Set(current.map((f) => f.name))
      return [...current, ...picked.filter((f) => !names.has(f.name))].slice(0, 20)
    })
  }

  const onDrop = (event: DragEvent) => {
    event.preventDefault()
    setDragging(false)
    add(event.dataTransfer.files)
  }

  const submit = async (event: FormEvent) => {
    event.preventDefault()
    const results: Outcome[] = files.map((f) => ({ name: f.name, state: 'waiting' }))
    setOutcomes([...results])
    for (const [index, file] of files.entries()) {
      if (file.size > maxBytes) {
        results[index] = { name: file.name, state: 'failed', message: `Larger than ${catalog.max_upload_mb} MB.` }
        setOutcomes([...results])
        continue
      }
      results[index] = { name: file.name, state: 'uploading' }
      setOutcomes([...results])
      try {
        const job = await upload.mutateAsync({ file, idField, titleField })
        results[index] = { name: file.name, state: 'done', message: runSummary(job.result) }
      } catch (error) {
        results[index] = { name: file.name, state: 'failed', message: errorMessage(error) }
      }
      setOutcomes([...results])
    }
    setFiles([])
  }

  const shown: Outcome[] = outcomes.length ? outcomes : files.map((f) => ({ name: f.name, state: 'waiting' }))

  return (
    <Dialog
      open
      onClose={busy ? () => {} : onClose}
      size="lg"
      title={`Import files into ${source.name}`}
      description="For exports, documents and sites that can't be fetched automatically. Each file is kept as permanent source records."
      footer={
        finished ? (
          <Button onClick={onClose}>Done</Button>
        ) : (
          <>
            <Button variant="secondary" onClick={onClose} disabled={busy}>
              Cancel
            </Button>
            <Button type="submit" form="upload-form" loading={busy} disabled={!files.length}>
              Import {files.length > 1 ? `${files.length} files` : 'file'}
            </Button>
          </>
        )
      }
    >
      <form id="upload-form" onSubmit={submit} className="space-y-4">
        <div
          onDragOver={(e) => {
            e.preventDefault()
            setDragging(true)
          }}
          onDragLeave={() => setDragging(false)}
          onDrop={onDrop}
          className={cn(
            'flex flex-col items-center rounded-2xl border-2 border-dashed px-4 py-8 text-center transition',
            dragging ? 'border-brand-400 bg-brand-50/60' : 'border-slate-200 bg-slate-50/60',
          )}
        >
          <FileUp className="mb-2 size-7 text-brand-500" aria-hidden />
          <p className="text-sm font-medium text-slate-800">Drop files here, or</p>
          <Button
            variant="secondary"
            size="sm"
            className="mt-2"
            onClick={() => input.current?.click()}
            disabled={busy}
          >
            Choose files
          </Button>
          <input
            ref={input}
            type="file"
            multiple
            hidden
            accept={catalog.upload_extensions.join(',')}
            onChange={(e) => {
              add(e.target.files)
              e.target.value = ''
            }}
            aria-label="Files to import"
          />
          <p className="mt-3 text-xs text-slate-500">
            {describeFileTypes(catalog.upload_extensions)} · up to {catalog.max_upload_mb} MB each
          </p>
        </div>

        {shown.length > 0 && (
          <ul className="divide-y divide-slate-100 rounded-xl ring-1 ring-slate-200">
            {shown.map((outcome) => (
              <li key={outcome.name} className="flex items-start gap-3 px-3 py-2.5 text-sm">
                {outcome.state === 'done' ? (
                  <CircleCheck className="mt-0.5 size-4 shrink-0 text-emerald-600" aria-label="Imported" />
                ) : outcome.state === 'failed' ? (
                  <TriangleAlert className="mt-0.5 size-4 shrink-0 text-rose-600" aria-label="Failed" />
                ) : outcome.state === 'uploading' ? (
                  <Spinner className="mt-0.5 size-4 shrink-0 text-brand-500" />
                ) : (
                  <FileUp className="mt-0.5 size-4 shrink-0 text-slate-400" aria-hidden />
                )}
                <div className="min-w-0 flex-1">
                  <p className="truncate font-medium text-slate-900">{outcome.name}</p>
                  {outcome.message && (
                    <p className={cn('text-xs', outcome.state === 'failed' ? 'text-rose-700' : 'text-slate-500')}>
                      {outcome.message}
                    </p>
                  )}
                </div>
                {!outcomes.length && (
                  <button
                    type="button"
                    onClick={() => setFiles((list) => list.filter((f) => f.name !== outcome.name))}
                    className="rounded p-1 text-slate-400 hover:bg-slate-100 hover:text-slate-700"
                    aria-label={`Remove ${outcome.name}`}
                  >
                    <X className="size-4" />
                  </button>
                )}
              </li>
            ))}
          </ul>
        )}

        {files.some((f) => TABULAR.test(f.name)) && (
          <div className="grid gap-4 sm:grid-cols-2">
            <TextField
              label="ID column (optional)"
              value={idField}
              onChange={(e) => setIdField(e.target.value)}
              placeholder="id"
              hint="Lets a re-imported row count as updated, not new."
            />
            <TextField
              label="Title column (optional)"
              value={titleField}
              onChange={(e) => setTitleField(e.target.value)}
              placeholder="question"
            />
          </div>
        )}
      </form>
    </Dialog>
  )
}
