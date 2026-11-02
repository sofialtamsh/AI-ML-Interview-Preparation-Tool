import { cn } from '../lib/cn'
import type { MasteryBand } from '../lib/types'

/** How well a student knows a topic (quiz and interview practice), not how far they got. */
export const MASTERY: Record<MasteryBand, { label: string; className: string }> = {
  strong: { label: 'Strong 💪', className: 'bg-emerald-50 text-emerald-800 ring-emerald-200' },
  developing: { label: 'Getting there', className: 'bg-sky-50 text-sky-800 ring-sky-200' },
  needs_work: { label: 'Needs work', className: 'bg-amber-50 text-amber-900 ring-amber-200' },
  not_enough_evidence: { label: 'Not quizzed yet', className: 'bg-slate-100 text-slate-600 ring-slate-200' },
}

export function MasteryChip({ band }: { band: MasteryBand }) {
  const { label, className } = MASTERY[band]
  return <span className={cn('inline-flex rounded-full px-2 py-0.5 text-xs font-semibold whitespace-nowrap ring-1', className)}>{label}</span>
}

export function ProgressBar({ value, label, className }: { value: number; label: string; className?: string }) {
  return (
    <div className={cn('h-2 overflow-hidden rounded-full bg-slate-200', className)} role="progressbar" aria-label={label} aria-valuemin={0} aria-valuemax={100} aria-valuenow={value}>
      <div className="h-full rounded-full bg-gradient-to-r from-brand-500 to-fuchsia-500 transition-all" style={{ width: `${value}%` }} />
    </div>
  )
}
