import { Check, Clock, X } from 'lucide-react'
import { useState } from 'react'
import { Link } from 'react-router'

import { Button } from '../../../components/ui/Button'
import { Dialog } from '../../../components/ui/Dialog'
import { Alert, Badge } from '../../../components/ui/Feedback'
import { TextField } from '../../../components/ui/Field'
import { useToast } from '../../../components/ui/Toast'
import { errorMessage } from '../../../lib/api'
import { timeAgo } from '../../../lib/format'
import type { Recommendation } from '../../../lib/types'
import { useCan } from '../../api'
import { useDecideRecommendation } from '../../intelApi'

export function recommendationTitle(rec: Recommendation): string {
  switch (rec.kind) {
    case 'add_topic':
      return `Add “${rec.proposed_name}” to ${rec.domain?.name ?? 'the taxonomy'}`
    case 'prioritize':
      return `Prioritise ${rec.topic?.name ?? 'a topic'}`
    case 'deprioritize':
      return `Deprioritise ${rec.topic?.name ?? 'a topic'}`
    default:
      return `Update content for ${rec.topic?.name ?? 'a topic'}`
  }
}

const STATUS = {
  pending: { tone: 'warning', label: 'Waiting for a decision' },
  approved: { tone: 'success', label: 'Approved' },
  rejected: { tone: 'neutral', label: 'Rejected' },
  deferred: { tone: 'neutral', label: 'Deferred' },
} as const

export function RecommendationCard({ rec, showReport = true }: { rec: Recommendation; showReport?: boolean }) {
  const canDecide = useCan('taxonomy.manage')
  const decide = useDecideRecommendation()
  const toast = useToast()
  const [confirming, setConfirming] = useState(false)
  const [note, setNote] = useState('')
  const open = rec.status === 'pending' || rec.status === 'deferred'

  const send = (decision: 'approved' | 'rejected' | 'deferred') =>
    decide.mutate(
      { id: rec.id, decision, note },
      {
        onSuccess: () => {
          setConfirming(false)
          toast.success(
            decision === 'approved'
              ? rec.kind === 'add_topic'
                ? `Added “${rec.proposed_name}” to the taxonomy. No content was generated.`
                : 'Approved. It will inform content planning; nothing was generated.'
              : decision === 'rejected'
                ? 'Rejected'
                : 'Deferred for later',
          )
        },
        onError: (e) => toast.error(errorMessage(e)),
      },
    )

  return (
    <div className="rounded-xl p-4 ring-1 ring-slate-200">
      <div className="flex flex-wrap items-start justify-between gap-2">
        <p className="font-medium text-slate-900">{recommendationTitle(rec)}</p>
        <Badge tone={STATUS[rec.status].tone}>{STATUS[rec.status].label}</Badge>
      </div>
      <p className="mt-1 text-sm text-slate-600">{rec.rationale}</p>
      <p className="mt-2 text-xs text-slate-500">
        Based on {rec.finding_ids.length} cited finding{rec.finding_ids.length === 1 ? '' : 's'}
        {showReport && (
          <>
            {' '}in{' '}
            <Link to={`/admin/agents/research/${rec.report_id}`} className="font-semibold text-brand-700 hover:underline">
              {rec.report_title}
            </Link>
          </>
        )}
        {rec.decided_by && ` · ${rec.status} by ${rec.decided_by} ${timeAgo(rec.decided_at).toLowerCase()}`}
      </p>
      {rec.decision_note && <p className="mt-1 text-xs text-slate-500">Note: {rec.decision_note}</p>}
      {canDecide && open && (
        <div className="mt-3 flex flex-wrap justify-end gap-2">
          {rec.status === 'pending' && (
            <Button variant="ghost" size="sm" icon={<Clock className="size-3.5" />} onClick={() => send('deferred')} disabled={decide.isPending}>
              Later
            </Button>
          )}
          <Button variant="secondary" size="sm" icon={<X className="size-3.5" />} onClick={() => send('rejected')} disabled={decide.isPending}>
            Reject
          </Button>
          <Button size="sm" icon={<Check className="size-3.5" />} onClick={() => setConfirming(true)} disabled={decide.isPending}>
            Approve
          </Button>
        </div>
      )}
      <Dialog
        open={confirming}
        onClose={() => setConfirming(false)}
        title="Approve this recommendation?"
        footer={
          <>
            <Button variant="secondary" onClick={() => setConfirming(false)}>
              Cancel
            </Button>
            <Button loading={decide.isPending} onClick={() => send('approved')}>
              Approve
            </Button>
          </>
        }
      >
        <div className="space-y-4 text-sm text-slate-600">
          {decide.isError && <Alert>{errorMessage(decide.error)}</Alert>}
          <p>
            {rec.kind === 'add_topic' ? (
              <>
                This adds <strong className="text-slate-900">{rec.proposed_name}</strong> to {rec.domain?.name} in the
                taxonomy, as a non-pilot topic.
              </>
            ) : (
              <>This records your decision so content planning can take it into account.</>
            )}{' '}
            It does <strong className="text-slate-900">not</strong> generate or publish any content.
          </p>
          <TextField label="Note (optional)" value={note} onChange={(e) => setNote(e.target.value)} maxLength={1000} />
        </div>
      </Dialog>
    </div>
  )
}
