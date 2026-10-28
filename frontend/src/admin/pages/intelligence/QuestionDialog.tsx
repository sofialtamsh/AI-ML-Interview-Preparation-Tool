import { Check, ExternalLink, Pencil, TriangleAlert, Undo2, X } from 'lucide-react'
import { useState } from 'react'

import { Button } from '../../../components/ui/Button'
import { Dialog } from '../../../components/ui/Dialog'
import { Alert, Badge, Skeleton } from '../../../components/ui/Feedback'
import { SelectField, TextField } from '../../../components/ui/Field'
import { useToast } from '../../../components/ui/Toast'
import { errorMessage } from '../../../lib/api'
import { formatDay } from '../../../lib/format'
import type { Difficulty, InterviewQuestionDetail, ReviewStatus } from '../../../lib/types'
import { useCan } from '../../api'
import { useCorrectInterview, useQuestion, useReviewQuestion, useTaxonomy } from '../../intelApi'
import { ReviewBadge } from './shared'

function InterviewDetails({ question }: { question: InterviewQuestionDetail }) {
  const canReview = useCan('intelligence.review')
  const correct = useCorrectInterview()
  const toast = useToast()
  const [editing, setEditing] = useState(false)
  const e = question.experience
  const [values, setValues] = useState({
    company: e.company ?? '',
    role: e.role ?? '',
    period: e.period ?? '',
    location: e.location ?? '',
  })

  if (editing) {
    return (
      <form
        className="space-y-3 rounded-xl bg-slate-50 p-4 ring-1 ring-slate-200"
        onSubmit={(event) => {
          event.preventDefault()
          correct.mutate(
            { id: e.id, ...values },
            {
              onSuccess: () => {
                toast.success('Interview details corrected. The original values stay in the audit log.')
                setEditing(false)
              },
            },
          )
        }}
      >
        {correct.isError && <Alert>{errorMessage(correct.error)}</Alert>}
        <div className="grid gap-3 sm:grid-cols-2">
          {(['company', 'role', 'period', 'location'] as const).map((field) => (
            <TextField
              key={field}
              label={field.charAt(0).toUpperCase() + field.slice(1)}
              value={values[field]}
              onChange={(ev) => setValues((v) => ({ ...v, [field]: ev.target.value }))}
              maxLength={field === 'period' ? 100 : 200}
            />
          ))}
        </div>
        <p className="text-xs text-slate-500">
          Only enter what the source record states. Corrections apply to every question from this interview.
        </p>
        <div className="flex justify-end gap-2">
          <Button variant="secondary" size="sm" onClick={() => setEditing(false)}>
            Cancel
          </Button>
          <Button type="submit" size="sm" loading={correct.isPending}>
            Save details
          </Button>
        </div>
      </form>
    )
  }
  return (
    <dl className="grid grid-cols-2 gap-x-4 gap-y-2 rounded-xl bg-slate-50 p-4 text-sm ring-1 ring-slate-200 sm:grid-cols-3">
      {[
        ['Company', e.company ?? 'Not stated'],
        ['Role', e.role ?? 'Not stated'],
        ['When', e.interview_date ? formatDay(e.interview_date) : (e.period ?? 'Not stated')],
        ['Round', question.round ?? 'Not stated'],
        ['Location', e.location ?? 'Not stated'],
        ['Source', question.source.name],
      ].map(([label, value]) => (
        <div key={label} className="min-w-0">
          <dt className="text-xs text-slate-500">{label}</dt>
          <dd className="truncate text-slate-900">{value}</dd>
        </div>
      ))}
      {canReview && (
        <div className="col-span-2 sm:col-span-3">
          <button
            type="button"
            onClick={() => setEditing(true)}
            className="inline-flex items-center gap-1 text-xs font-semibold text-brand-700 hover:underline"
          >
            <Pencil className="size-3" aria-hidden /> Correct interview details
          </button>
        </div>
      )}
    </dl>
  )
}

function ReviewForm({ question, onDone }: { question: InterviewQuestionDetail; onDone: () => void }) {
  const taxonomy = useTaxonomy()
  const review = useReviewQuestion()
  const toast = useToast()
  const [topicId, setTopicId] = useState(question.topic?.id ?? '')
  const [difficulty, setDifficulty] = useState<Difficulty | ''>(question.difficulty ?? '')
  const [round, setRound] = useState(question.round ?? '')
  const [note, setNote] = useState(question.review_note ?? '')

  const save = (status?: ReviewStatus) =>
    review.mutate(
      {
        id: question.id,
        ...(status ? { status } : {}),
        topic_id: topicId || null,
        difficulty: difficulty || null,
        round: round.trim() || null,
        review_note: note.trim() || null,
      },
      {
        onSuccess: () => {
          toast.success(
            status === 'approved' ? 'Approved' : status === 'rejected' ? 'Rejected' : status ? 'Moved back to review' : 'Saved',
          )
          if (status) onDone()
        },
      },
    )

  return (
    <section className="space-y-3">
      {review.isError && <Alert>{errorMessage(review.error)}</Alert>}
      <div className="grid gap-3 sm:grid-cols-3">
        <SelectField label="Topic" value={topicId} onChange={(e) => setTopicId(e.target.value)}>
          <option value="">No topic</option>
          {taxonomy.data?.map((domain) => (
            <optgroup key={domain.id} label={domain.name}>
              {domain.topics.map((t) => (
                <option key={t.id} value={t.id}>
                  {t.name}
                </option>
              ))}
            </optgroup>
          ))}
        </SelectField>
        <SelectField
          label="Difficulty"
          value={difficulty}
          onChange={(e) => setDifficulty(e.target.value as Difficulty | '')}
        >
          <option value="">Not stated</option>
          <option value="easy">Easy</option>
          <option value="medium">Medium</option>
          <option value="hard">Hard</option>
        </SelectField>
        <TextField label="Round" value={round} onChange={(e) => setRound(e.target.value)} maxLength={200} />
      </div>
      <TextField
        label="Review note (optional)"
        value={note}
        onChange={(e) => setNote(e.target.value)}
        maxLength={500}
        placeholder="e.g. Paraphrased in the source"
      />
      <div className="flex flex-wrap justify-end gap-2">
        <Button variant="ghost" onClick={() => save()} loading={review.isPending && !review.variables?.status}>
          Save changes
        </Button>
        {question.status !== 'pending_review' && (
          <Button variant="secondary" icon={<Undo2 className="size-4" />} onClick={() => save('pending_review')}>
            Back to review
          </Button>
        )}
        {question.status !== 'rejected' && (
          <Button variant="secondary" icon={<X className="size-4" />} onClick={() => save('rejected')}>
            Reject
          </Button>
        )}
        {question.status !== 'approved' && (
          <Button icon={<Check className="size-4" />} onClick={() => save('approved')}>
            Approve
          </Button>
        )}
      </div>
    </section>
  )
}

export function QuestionDialog({ id, onClose }: { id: string; onClose: () => void }) {
  const question = useQuestion(id)
  const canReview = useCan('intelligence.review')
  const review = useReviewQuestion()
  const toast = useToast()
  const q = question.data

  return (
    <Dialog
      open
      onClose={onClose}
      size="lg"
      title="Interview question"
      description="Admin-only: company names and sources never reach students."
    >
      {question.isPending ? (
        <Skeleton className="h-64" />
      ) : question.isError ? (
        <Alert>{errorMessage(question.error)}</Alert>
      ) : (
        q && (
          <div className="space-y-5">
            <div>
              <div className="mb-2 flex flex-wrap items-center gap-1.5">
                <ReviewBadge status={q.status} />
                {!q.grounded && (
                  <Badge tone="warning">
                    <TriangleAlert className="size-3" aria-hidden /> Not word-for-word in the source
                  </Badge>
                )}
                {q.seen_in_records > 0 && <Badge tone="brand">Seen in {q.seen_in_records} approved record(s)</Badge>}
                {q.reviewed_by && (
                  <span className="text-xs text-slate-500">Reviewed by {q.reviewed_by}</span>
                )}
              </div>
              <blockquote className="rounded-xl border-l-4 border-brand-400 bg-brand-50/40 px-4 py-3 text-base text-slate-900">
                {q.original_text}
              </blockquote>
              {q.suggested_topic && !q.topic && (
                <p className="mt-2 text-xs text-slate-500">The agent suggested a new topic: “{q.suggested_topic}”.</p>
              )}
            </div>

            <InterviewDetails key={q.experience.id + q.experience.company} question={q} />

            <section>
              <h3 className="mb-2 flex items-center justify-between text-sm font-semibold text-slate-900">
                In the source
                {q.record.url && (
                  <a
                    href={q.record.url}
                    target="_blank"
                    rel="noreferrer noopener"
                    className="inline-flex items-center gap-1 text-xs font-semibold text-brand-700 hover:underline"
                  >
                    Open original <ExternalLink className="size-3" aria-hidden />
                  </a>
                )}
              </h3>
              <pre className="max-h-48 overflow-auto rounded-xl bg-slate-50 p-3 text-xs leading-relaxed whitespace-pre-wrap text-slate-700 ring-1 ring-slate-200">
                {q.context}
              </pre>
            </section>

            {(q.duplicate_of_text || q.duplicates.length > 0) && (
              <section className="space-y-2">
                <h3 className="text-sm font-semibold text-slate-900">Same question elsewhere</h3>
                {q.duplicate_of_text && (
                  <div className="flex items-start justify-between gap-3 rounded-xl p-3 text-sm ring-1 ring-slate-200">
                    <p className="text-slate-700">
                      <span className="text-xs font-semibold text-slate-500">Marked as a repeat of: </span>
                      {q.duplicate_of_text}
                    </p>
                    {canReview && (
                      <Button
                        variant="ghost"
                        size="sm"
                        loading={review.isPending}
                        onClick={() =>
                          review.mutate(
                            { id: q.id, duplicate_of_id: null },
                            { onSuccess: () => toast.success('No longer marked as a repeat') },
                          )
                        }
                      >
                        Not a repeat
                      </Button>
                    )}
                  </div>
                )}
                {q.duplicates.map((d) => (
                  <div key={d.id} className="flex items-start justify-between gap-3 rounded-xl p-3 text-sm ring-1 ring-slate-200">
                    <p className="text-slate-700">{d.original_text}</p>
                    <ReviewBadge status={d.status} />
                  </div>
                ))}
              </section>
            )}

            {canReview && <ReviewForm key={q.id + q.status} question={q} onDone={onClose} />}
          </div>
        )
      )}
    </Dialog>
  )
}
