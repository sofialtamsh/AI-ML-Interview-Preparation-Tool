import { Check, Copy, Pencil, Play, RotateCcw, Database, TriangleAlert, Rocket } from 'lucide-react'
import { useState } from 'react'

import { Button } from '../../components/ui/Button'
import { Badge } from '../../components/ui/Feedback'
import { normaliseOutput, runPython, type RunResult, type RunStatus } from '../../lib/pyodide'
import type { PythonLabContent } from '../../lib/types'
import { PythonCode } from '../PythonCode'
import { RichText } from '../RichText'

export function CodeLab({ lab, editable = true }: { lab: PythonLabContent; editable?: boolean }) {
  const [codes, setCodes] = useState(() => lab.steps.map((s) => s.code))
  const [editing, setEditing] = useState<number | null>(null)
  const [copied, setCopied] = useState<number | null>(null)
  const [status, setStatus] = useState<RunStatus | null>(null)
  const [result, setResult] = useState<RunResult | null>(null)
  const [showExpected, setShowExpected] = useState(false)

  const edited = codes.some((code, i) => code !== lab.steps[i].code)
  const program = codes.join('\n\n')

  const run = async () => {
    setResult(null)
    setStatus('loading')
    const outcome = await runPython(program, lab.packages, setStatus)
    setStatus(null)
    setResult(outcome)
  }

  const copy = async (i: number) => {
    try {
      await navigator.clipboard.writeText(codes[i])
      setCopied(i)
      window.setTimeout(() => setCopied(null), 1500)
    } catch {
      setCopied(null)
    }
  }

  const matches = result && !result.error && normaliseOutput(result.output) === normaliseOutput(lab.expected_output)

  return (
    <div className="space-y-5">
      <div className="space-y-2">
        <p className="flex gap-2 text-slate-700">
          <Database className="mt-1 size-4 shrink-0 text-brand-600" aria-hidden />
          <span>
            <span className="font-semibold text-slate-900">The data: </span>
            <RichText text={lab.dataset} />
          </span>
        </p>
        <div className="flex flex-wrap items-center gap-2">
          {lab.packages.map((p) => (
            <Badge key={p}>{p}</Badge>
          ))}
          <span className="text-xs text-slate-500">Runs right in your browser. Nothing to install.</span>
        </div>
      </div>

      <ol className="space-y-4">
        {lab.steps.map((step, i) => (
          <li key={i} className="rounded-3xl bg-white p-4 ring-1 ring-slate-200 sm:p-5">
            <div className="flex flex-wrap items-start justify-between gap-2">
              <h3 className="font-display text-lg font-bold text-slate-900">
                <span className="mr-2 inline-grid size-7 place-items-center rounded-full bg-brand-50 text-sm text-brand-700">{i + 1}</span>
                {step.title}
              </h3>
              <div className="flex gap-1">
                {codes[i] !== step.code && (
                  <Button size="sm" variant="ghost" icon={<RotateCcw className="size-4" />} onClick={() => setCodes(codes.map((c, j) => (j === i ? step.code : c)))}>
                    Reset
                  </Button>
                )}
                {editable && (
                  <Button size="sm" variant="ghost" icon={<Pencil className="size-4" />} onClick={() => setEditing(editing === i ? null : i)}>
                    {editing === i ? 'Done' : 'Edit'}
                  </Button>
                )}
                <Button size="sm" variant="ghost" icon={copied === i ? <Check className="size-4" /> : <Copy className="size-4" />} onClick={() => copy(i)}>
                  {copied === i ? 'Copied' : 'Copy'}
                </Button>
              </div>
            </div>
            <p className="mt-1 mb-3 text-slate-600">
              <RichText text={step.explanation} />
            </p>
            {editing === i ? (
              <textarea
                aria-label={`Code for step ${i + 1}`}
                value={codes[i]}
                onChange={(event) => setCodes(codes.map((c, j) => (j === i ? event.target.value : c)))}
                spellCheck={false}
                rows={Math.max(4, codes[i].split('\n').length + 1)}
                className="w-full rounded-2xl bg-slate-950 p-4 font-mono text-[13px] leading-relaxed text-slate-100 outline-none focus:ring-2 focus:ring-brand-400"
              />
            ) : (
              <PythonCode code={codes[i]} />
            )}
          </li>
        ))}
      </ol>

      <section className="rounded-3xl bg-slate-900 p-4 text-white sm:p-5" aria-live="polite">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div>
            <h3 className="font-display text-lg font-bold">Run it</h3>
            <p className="text-sm text-slate-300">All steps run in order{edited ? ', with your edits' : ''}.</p>
          </div>
          <div className="flex flex-wrap gap-2">
            <Button variant="glow" icon={<Play className="size-4" />} loading={status !== null} onClick={run}>
              {status === 'loading' ? 'Loading Python…' : status === 'running' ? 'Running…' : 'Run all steps'}
            </Button>
            <Button variant="secondary" onClick={() => setShowExpected(!showExpected)}>
              {showExpected ? 'Hide' : 'Show'} expected output
            </Button>
          </div>
        </div>
        {status === 'loading' && (
          <p className="mt-3 text-sm text-slate-300">The first run downloads Python and its libraries (about 30 MB), so give it a moment. Later runs are quick.</p>
        )}
        {result && (
          <div className="mt-4 space-y-2">
            {result.error ? (
              <p className="flex items-center gap-1.5 text-sm font-semibold text-rose-300">
                <TriangleAlert className="size-4" aria-hidden /> Python raised an error
              </p>
            ) : matches ? (
              <p className="flex items-center gap-1.5 text-sm font-semibold text-emerald-300">
                <Rocket className="size-4" aria-hidden /> Matches the expected output · {result.durationMs} ms
              </p>
            ) : (
              <p className="text-sm text-amber-200">
                Output differs from the expected one{edited ? ', which makes sense after your edits' : ''}. · {result.durationMs} ms
              </p>
            )}
            {result.output && <pre className="overflow-x-auto rounded-2xl bg-black/40 p-4 font-mono text-[13px] whitespace-pre-wrap text-slate-100">{result.output}</pre>}
            {result.stderr && <pre className="overflow-x-auto rounded-2xl bg-amber-950/40 p-3 font-mono text-xs whitespace-pre-wrap text-amber-200">{result.stderr}</pre>}
            {result.error && <pre className="overflow-x-auto rounded-2xl bg-rose-950/50 p-4 font-mono text-xs whitespace-pre-wrap text-rose-200">{result.error}</pre>}
          </div>
        )}
        {showExpected && (
          <div className="mt-4">
            <p className="text-xs font-semibold tracking-wide text-slate-400 uppercase">Expected output</p>
            <pre className="mt-1 overflow-x-auto rounded-2xl bg-black/40 p-4 font-mono text-[13px] whitespace-pre-wrap text-slate-200">{lab.expected_output}</pre>
          </div>
        )}
      </section>

      <div className="grid gap-4 md:grid-cols-2">
        <section className="rounded-3xl bg-white p-5 ring-1 ring-slate-200">
          <h3 className="font-display text-lg font-bold text-slate-900">🚧 Common mistakes</h3>
          <ul className="mt-2 space-y-2 text-slate-700">
            {lab.mistakes.map((m, i) => (
              <li key={i} className="flex gap-2">
                <span aria-hidden>•</span>
                <span>
                  <RichText text={m} />
                </span>
              </li>
            ))}
          </ul>
        </section>
        <section className="rounded-3xl bg-white p-5 ring-1 ring-slate-200">
          <h3 className="font-display text-lg font-bold text-slate-900">🌍 Where this shows up</h3>
          <ul className="mt-2 space-y-2 text-slate-700">
            {lab.applications.map((a, i) => (
              <li key={i} className="flex gap-2">
                <span aria-hidden>•</span>
                <span>
                  <RichText text={a} />
                </span>
              </li>
            ))}
          </ul>
        </section>
      </div>
    </div>
  )
}
