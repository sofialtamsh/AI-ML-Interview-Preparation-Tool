import { X } from 'lucide-react'
import { useEffect, useId, useRef, type ReactNode } from 'react'

import { cn } from '../../lib/cn'

/** Native <dialog> as a modal: focus trapping, Esc and the backdrop come from the browser. */
export function Dialog({
  open,
  onClose,
  title,
  description,
  children,
  footer,
  size = 'md',
}: {
  open: boolean
  onClose: () => void
  title: string
  description?: ReactNode
  children: ReactNode
  footer?: ReactNode
  size?: 'md' | 'lg'
}) {
  const ref = useRef<HTMLDialogElement>(null)
  const titleId = useId()

  useEffect(() => {
    const dialog = ref.current
    if (!dialog) return
    if (open && !dialog.open) dialog.showModal?.()
    if (!open && dialog.open) dialog.close?.()
  }, [open])

  return (
    <dialog
      ref={ref}
      aria-labelledby={titleId}
      onClose={onClose}
      onClick={(event) => event.target === ref.current && onClose()}
      className={cn(
        'm-auto w-[calc(100%-2rem)] rounded-2xl bg-white p-0 text-slate-900 shadow-2xl ring-1 ring-slate-200 open:animate-pop',
        size === 'lg' ? 'max-w-2xl' : 'max-w-lg',
      )}
    >
      {open && (
        <div className="flex max-h-[85dvh] flex-col">
          <div className="flex items-start justify-between gap-4 border-b border-slate-100 px-6 py-4">
            <div>
              <h2 id={titleId} className="font-display text-lg font-semibold">
                {title}
              </h2>
              {description && <p className="mt-0.5 text-sm text-slate-500">{description}</p>}
            </div>
            <button
              type="button"
              onClick={onClose}
              className="-mr-2 rounded-lg p-1.5 text-slate-400 transition hover:bg-slate-100 hover:text-slate-700"
              aria-label="Close"
            >
              <X className="size-5" />
            </button>
          </div>
          <div className="overflow-y-auto px-6 py-5">{children}</div>
          {footer && (
            <div className="flex justify-end gap-2 border-t border-slate-100 bg-slate-50/60 px-6 py-3.5">
              {footer}
            </div>
          )}
        </div>
      )}
    </dialog>
  )
}
