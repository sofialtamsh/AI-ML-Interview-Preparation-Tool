import { Badge } from '../components/ui/Feedback'
import type { AdminStatus, StudentStatus } from '../lib/types'

const TONES = {
  active: 'success',
  suspended: 'warning',
  deactivated: 'neutral',
  disabled: 'danger',
} as const

const LABELS = {
  active: 'Active',
  suspended: 'Suspended',
  deactivated: 'Deactivated',
  disabled: 'Disabled',
} as const

export function StatusBadge({ status }: { status: StudentStatus | AdminStatus }) {
  return (
    <Badge tone={TONES[status]}>
      <span className="size-1.5 rounded-full bg-current" aria-hidden />
      {LABELS[status]}
    </Badge>
  )
}
