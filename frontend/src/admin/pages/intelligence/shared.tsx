import { Badge } from '../../../components/ui/Feedback'
import type { ReviewStatus } from '../../../lib/types'

const REVIEW = {
  pending_review: { tone: 'warning', label: 'Waiting for review' },
  approved: { tone: 'success', label: 'Approved' },
  rejected: { tone: 'neutral', label: 'Rejected' },
} as const

export function ReviewBadge({ status }: { status: ReviewStatus }) {
  const { tone, label } = REVIEW[status]
  return (
    <Badge tone={tone}>
      <span className="size-1.5 rounded-full bg-current" aria-hidden />
      {label}
    </Badge>
  )
}
