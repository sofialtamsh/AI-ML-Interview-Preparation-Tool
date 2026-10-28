/** Runs Python in the browser with Pyodide, inside a Web Worker.
 *
 * Code never runs on our server: it runs in the visitor's own browser sandbox, off the main
 * thread, with a fresh namespace per run and a hard time limit (the worker is terminated). */

export const PYODIDE_VERSION = '314.0.7'
export const PYODIDE_RUNTIME = `pyodide-${PYODIDE_VERSION}`
const PYODIDE_URL = `https://cdn.jsdelivr.net/pyodide/v${PYODIDE_VERSION}/full/pyodide.mjs`

const LOAD_TIMEOUT_MS = 240_000
export const RUN_TIMEOUT_MS = 30_000

const WORKER_SOURCE = `
let pyodide = null
let loading = null
self.onmessage = async (event) => {
  const { id, code, packages } = event.data
  const say = (message) => self.postMessage({ id, ...message })
  try {
    say({ type: 'status', status: 'loading' })
    // threadpoolctl (pulled in by scikit-learn) trips a Pyodide deprecation warning on import;
    // it is Pyodide-internal noise, not the student's code, so it is silenced.
    if (!loading) loading = import(${JSON.stringify(PYODIDE_URL)})
      .then((m) => m.loadPyodide())
      .then((py) => {
        py.runPython("import warnings; warnings.filterwarnings('ignore', module='threadpoolctl')")
        return py
      })
    pyodide = await loading
    if (packages.length) await pyodide.loadPackage(packages)
    await pyodide.loadPackagesFromImports(code)
  } catch (err) {
    say({ type: 'done', output: '', stderr: '', error: 'Could not load Python: ' + (err && err.message ? err.message : err), duration: 0 })
    return
  }
  say({ type: 'status', status: 'running' })
  let output = ''
  let stderr = ''
  pyodide.setStdout({ batched: (line) => { output += line + '\\n' } })
  pyodide.setStderr({ batched: (line) => { stderr += line + '\\n' } })
  const globals = pyodide.toPy({})
  const started = performance.now()
  let error = null
  try {
    await pyodide.runPythonAsync(code, { globals })
  } catch (err) {
    error = String(err && err.message ? err.message : err)
  } finally {
    globals.destroy()
  }
  say({ type: 'done', output, stderr, error, duration: Math.round(performance.now() - started) })
}
`

export type RunStatus = 'loading' | 'running'
export type RunResult = { output: string; stderr: string; error: string | null; durationMs: number }

let worker: Worker | null = null
let nextId = 1

function getWorker(): Worker {
  if (!worker) {
    const url = URL.createObjectURL(new Blob([WORKER_SOURCE], { type: 'text/javascript' }))
    worker = new Worker(url, { type: 'module' })
  }
  return worker
}

function stopWorker() {
  worker?.terminate()
  worker = null
}

/** Run a program; resolves with stdout, stderr and the Python error (if any). Never rejects. */
export function runPython(code: string, packages: string[], onStatus?: (status: RunStatus) => void): Promise<RunResult> {
  const id = nextId++
  const target = getWorker()
  return new Promise((resolve) => {
    let timer = window.setTimeout(() => finish(timeout('Loading Python took too long. Check your connection and try again.')), LOAD_TIMEOUT_MS)
    const timeout = (message: string): RunResult => {
      stopWorker()
      return { output: '', stderr: '', error: message, durationMs: 0 }
    }
    const finish = (result: RunResult) => {
      window.clearTimeout(timer)
      target.removeEventListener('message', onMessage)
      target.removeEventListener('error', onError)
      resolve(result)
    }
    const onMessage = (event: MessageEvent) => {
      const data = event.data
      if (data.id !== id) return
      if (data.type === 'status') {
        onStatus?.(data.status)
        if (data.status === 'running') {
          window.clearTimeout(timer)
          timer = window.setTimeout(
            () => finish(timeout(`Stopped after ${RUN_TIMEOUT_MS / 1000} seconds. Is there an endless loop?`)),
            RUN_TIMEOUT_MS,
          )
        }
        return
      }
      finish({ output: data.output, stderr: data.stderr, error: data.error, durationMs: data.duration })
    }
    const onError = (event: ErrorEvent) => {
      stopWorker()
      finish({ output: '', stderr: '', error: `Python worker failed: ${event.message || 'unknown error'}`, durationMs: 0 })
    }
    target.addEventListener('message', onMessage)
    target.addEventListener('error', onError)
    target.postMessage({ id, code, packages })
  })
}

/** Mirrors the server's comparison (app/content/service.py normalise_output). */
export const normaliseOutput = (text: string) =>
  text
    .trim()
    .split(/\r?\n/)
    .map((line) => line.trimEnd())
    .join('\n')
