import { CircleCheck, TriangleAlert, X } from 'lucide-react'
import { createContext, useCallback, useContext, useMemo, useState, type ReactNode } from 'react'

type Toast = { id: number; tone: 'success' | 'error'; message: string }
type ToastApi = { success: (message: string) => void; error: (message: string) => void }

const ToastContext = createContext<ToastApi | null>(null)

let nextId = 1

export function ToastProvider({ children }: { children: ReactNode }) {
  const [toasts, setToasts] = useState<Toast[]>([])

  const dismiss = useCallback((id: number) => {
    setToasts((current) => current.filter((t) => t.id !== id))
  }, [])

  const push = useCallback(
    (tone: Toast['tone'], message: string) => {
      const id = nextId++
      setToasts((current) => [...current.slice(-2), { id, tone, message }])
      window.setTimeout(() => dismiss(id), 4500)
    },
    [dismiss],
  )

  const api = useMemo<ToastApi>(
    () => ({ success: (m) => push('success', m), error: (m) => push('error', m) }),
    [push],
  )

  return (
    <ToastContext.Provider value={api}>
      {children}
      <div
        aria-live="polite"
        className="pointer-events-none fixed inset-x-0 bottom-20 z-50 flex flex-col items-center gap-2 px-4 sm:bottom-6 sm:items-end"
      >
        {toasts.map((toast) => (
          <div
            key={toast.id}
            role="status"
            className="pointer-events-auto flex w-full max-w-sm animate-fade-up items-start gap-3 rounded-2xl bg-slate-900 px-4 py-3 text-sm text-white shadow-xl shadow-slate-900/20"
          >
            {toast.tone === 'success' ? (
              <CircleCheck aria-hidden className="mt-0.5 size-4 shrink-0 text-lime-300" />
            ) : (
              <TriangleAlert aria-hidden className="mt-0.5 size-4 shrink-0 text-rose-300" />
            )}
            <p className="flex-1">{toast.message}</p>
            <button
              type="button"
              onClick={() => dismiss(toast.id)}
              className="-m-1 rounded p-1 text-slate-400 hover:text-white"
              aria-label="Dismiss"
            >
              <X className="size-4" />
            </button>
          </div>
        ))}
      </div>
    </ToastContext.Provider>
  )
}

export function useToast(): ToastApi {
  const context = useContext(ToastContext)
  if (!context) throw new Error('useToast must be used inside <ToastProvider>')
  return context
}
