import { Eye, Lock, Mic, Trash2, Wand2 } from 'lucide-react'
import { useState, type ReactNode } from 'react'

import { Button } from '../../components/ui/Button'
import { Alert, Skeleton } from '../../components/ui/Feedback'
import { AnswerRecorder } from '../../learn/practice/AnswerRecorder'
import { FeedbackView } from '../../learn/practice/FeedbackView'
import type { Recording } from '../../learn/practice/useAnswerRecorder'
import { errorMessage } from '../../lib/api'
import { cn } from '../../lib/cn'
import { timeAgo } from '../../lib/format'
import type { AttemptDetail, AttemptSummary, InterviewEntry } from '../../lib/types'
import { useDeleteAttempt, usePracticeAttempt, usePracticeAttempts, usePracticeStatus, useSubmitAnswer } from '../practiceApi'

function scoreTone(score: number | null): string {
  if (score === null) return 'bg-slate-100 text-slate-600'
  if (score >= 8) return 'bg-emerald-100 text-emerald-800'
  if (score >= 6) return 'bg-sky-100 text-sky-800'
  if (score >= 4) return 'bg-amber-100 text-amber-900'
  return 'bg-orange-100 text-orange-900'
}

const STATUS_LABEL: Record<AttemptSummary['status'], string> = {
  queued: 'In line',
  processing: 'Scoring…',
  completed: '',
  no_answer: 'No answer heard',
  failed: "Didn't work",
}

function Working({ attempt }: { attempt: AttemptDetail }) {
  const steps = [
    { label: '🎧 Listening to your answer', done: attempt.transcript !== null },
    { label: '🧠 Thinking like an interviewer', done: false },
  ]
  const current = attempt.status === 'queued' ? -1 : attempt.transcript === null ? 0 : 1
  return (
    <div className="rounded-3xl bg-gradient-to-br from-brand-50 to-fuchsia-50 p-5 ring-1 ring-brand-100" aria-live="polite">
      <p className="font-display font-bold text-slate-900">{attempt.status === 'queued' ? '⏳ Getting ready…' : 'Your AI coach is on it'}</p>
      <ol className="mt-3 space-y-2">
        {steps.map((step, i) => (
          <li key={step.label} className={cn('flex items-center gap-2 text-sm', i === current ? 'font-semibold text-slate-900' : step.done ? 'text-slate-500 line-through' : 'text-slate-400')}>
            <span className={cn('size-2 rounded-full', i === current ? 'animate-pulse bg-brand-600' : step.done ? 'bg-emerald-500' : 'bg-slate-300')} aria-hidden />
            {step.label}
          </li>
        ))}
      </ol>
      <p className="mt-3 text-xs text-slate-500">Usually 15–40 seconds. You can keep scrolling; it carries on.</p>
    </div>
  )
}

function AttemptResult({ id, onDeleted }: { id: string; onDeleted: () => void }) {
  const attempt = usePracticeAttempt(id)
  const remove = useDeleteAttempt()
  const [confirming, setConfirming] = useState(false)

  if (attempt.isPending) return <Skeleton className="h-40 rounded-3xl" />
  if (attempt.isError) return <Alert>{errorMessage(attempt.error)}</Alert>
  const data = attempt.data
  if (data.status === 'queued' || data.status === 'processing') return <Working attempt={data} />
  if (data.status === 'failed') return <Alert>{data.error ?? 'That didn’t work. Try again.'}</Alert>

  return (
    <div className="space-y-3">
      {data.status === 'no_answer' ? (
        <div className="rounded-3xl bg-amber-50 p-5 ring-1 ring-amber-100">
          <p className="font-display font-bold text-slate-900">🤫 We could barely hear an answer</p>
          <p className="mt-1 text-sm text-slate-700">Check that your mic is on and close enough, then give it a full go. Nothing was scored.</p>
          {data.transcript && <p className="mt-2 text-sm text-slate-500 italic">We heard: &ldquo;{data.transcript}&rdquo;</p>}
        </div>
      ) : (
        data.feedback && <FeedbackView feedback={data.feedback} delivery={data.delivery} transcript={data.transcript} />
      )}
      <div className="flex items-center justify-end gap-2 text-sm">
        {remove.isError && <span className="text-rose-700">{errorMessage(remove.error)}</span>}
        {confirming ? (
          <>
            <span className="text-slate-600">Delete this try for good?</span>
            <Button size="sm" variant="danger" loading={remove.isPending} onClick={() => remove.mutate(data, { onSuccess: onDeleted })}>
              Delete
            </Button>
            <Button size="sm" variant="ghost" onClick={() => setConfirming(false)}>
              Keep
            </Button>
          </>
        ) : (
          <Button size="sm" variant="ghost" onClick={() => setConfirming(true)} icon={<Trash2 className="size-4" />}>
            Delete this try
          </Button>
        )}
      </div>
    </div>
  )
}

/** The strong answer, unlocked by the student's first take so they try before they peek. */
function StrongAnswerGate({ unlocked, cannotRecord, children }: { unlocked: boolean; cannotRecord: boolean; children: ReactNode }) {
  const [revealed, setRevealed] = useState(false)
  if (revealed) return <div className="animate-fade-up space-y-3">{children}</div>
  if (!unlocked && !cannotRecord) {
    return (
      <p className="flex items-center justify-center gap-2 rounded-2xl border border-dashed border-slate-300 px-4 py-3 text-center text-sm text-slate-500">
        <Lock className="size-4 shrink-0" aria-hidden /> The strong answer and what the interviewer wants unlock after your first take.
      </p>
    )
  }
  return (
    <button
      type="button"
      onClick={() => setRevealed(true)}
      className="flex w-full items-center justify-center gap-2 rounded-2xl border border-dashed border-slate-300 px-4 py-3 text-sm font-semibold text-slate-600 hover:border-slate-400 hover:bg-slate-50"
    >
      <Eye className="size-4" aria-hidden /> {unlocked ? 'Show the strong answer' : "Can't record right now? Show the strong answer"}
    </button>
  )
}

/** Record an answer to one interview question and get interviewer-style feedback on it. */
export function AnswerPractice({
  topic,
  versionId,
  index,
  item,
  strongAnswer,
  answered,
  onTake,
}: {
  topic: string
  versionId: string
  index: number
  item: InterviewEntry
  strongAnswer: ReactNode
  /** The student has recorded this question before (saved to their account). */
  answered: boolean
  /** A take was just recorded; the parent saves it to the student's progress. */
  onTake: () => void
}) {
  const status = usePracticeStatus()
  const attempts = usePracticeAttempts(topic)
  const submit = useSubmitAnswer()
  const [recording, setRecording] = useState(false)
  const [shown, setShown] = useState<string | null>(null)
  const [took, setTook] = useState(false)
  const [cannotRecord, setCannotRecord] = useState(false)

  const mine = (attempts.data ?? []).filter((a) => a.question === item.question)
  const left = status.data ? Math.max(0, status.data.daily_limit - status.data.used_today) : 0
  const gate = (
    <StrongAnswerGate unlocked={answered || took || mine.length > 0} cannotRecord={cannotRecord}>
      {strongAnswer}
    </StrongAnswerGate>
  )
  const markTaken = () => {
    setTook(true)
    onTake()
  }

  const feedbackAction = (take: Recording) => {
    if (shown) return null
    if (!status.data?.feedback_available) {
      return <span className="text-sm text-slate-600">{status.data?.reason ?? 'AI feedback is unavailable.'} You can still rewatch your answer.</span>
    }
    if (!take.wav) return <span className="text-sm text-slate-600">This browser couldn&apos;t prepare your audio for feedback. Try Chrome or Edge.</span>
    const wav = take.wav
    return (
      <Button
        variant="glow"
        loading={submit.isPending}
        icon={<Wand2 className="size-4" />}
        onClick={() => submit.mutate({ topic, versionId, questionIndex: index, wav }, { onSuccess: (attempt) => setShown(attempt.id) })}
      >
        Get AI feedback
      </Button>
    )
  }

  if (recording) {
    return (
      <div className="space-y-4 rounded-3xl bg-white p-4 ring-1 ring-brand-200 sm:p-5">
        <AnswerRecorder
          question={item.question}
          maxSeconds={status.data?.max_seconds ?? 180}
          actions={feedbackAction}
          onReset={() => {
            setShown(null)
            submit.reset()
          }}
          onRecorded={markTaken}
          onCannotRecord={() => setCannotRecord(true)}
          onClose={() => setRecording(false)}
        />
        {submit.isError && <Alert>{errorMessage(submit.error)}</Alert>}
        {shown && <AttemptResult id={shown} onDeleted={() => setShown(null)} />}
        {gate}
      </div>
    )
  }

  return (
    <div className="space-y-4">
      <div className="rounded-3xl bg-gradient-to-br from-brand-600 via-violet-600 to-fuchsia-600 p-5 text-white">
        <p className="font-display text-lg font-bold">🎤 Answer it like the real thing</p>
        <p className="mt-1 text-sm text-white/85">Record yourself (3 min max), then get scored the way an interviewer would, with tips and a stronger version of your answer.</p>
        <div className="mt-4 flex flex-wrap items-center gap-3">
          <Button
            variant="secondary"
            size="lg"
            icon={<Mic className="size-4" />}
            onClick={() => {
              setShown(null)
              submit.reset()
              setRecording(true)
            }}
          >
            Record my answer
          </Button>
          {status.data && (
            <span className="text-xs font-medium text-white/85">
              {status.data.feedback_available ? `AI feedback: ${left} of ${status.data.daily_limit} left today` : status.data.reason}
            </span>
          )}
        </div>
      </div>

      {mine.length > 0 && (
        <div>
          <p className="text-xs font-bold tracking-wide text-slate-500 uppercase">Your tries</p>
          <ul className="mt-2 flex flex-wrap gap-2">
            {mine.slice(0, 6).map((attempt) => (
              <li key={attempt.id}>
                <button
                  type="button"
                  aria-label={`${attempt.score !== null ? `${attempt.score.toFixed(1)} out of 10, ` : ''}${attempt.verdict ?? STATUS_LABEL[attempt.status]}, ${timeAgo(attempt.created_at)}`}
                  aria-pressed={shown === attempt.id}
                  onClick={() => setShown(shown === attempt.id ? null : attempt.id)}
                  className={cn('inline-flex items-center gap-2 rounded-full bg-white py-1 pr-3 pl-1 text-sm ring-1 transition hover:bg-slate-50', shown === attempt.id ? 'ring-2 ring-brand-500' : 'ring-slate-200')}
                >
                  <span className={cn('rounded-full px-2 py-0.5 text-xs font-bold tabular-nums', scoreTone(attempt.score))}>
                    {attempt.score !== null ? attempt.score.toFixed(1) : '—'}
                  </span>
                  <span className="font-medium text-slate-700">{attempt.verdict ?? STATUS_LABEL[attempt.status]}</span>
                  <span className="text-xs text-slate-400">{timeAgo(attempt.created_at)}</span>
                </button>
              </li>
            ))}
          </ul>
        </div>
      )}

      {shown && <AttemptResult id={shown} onDeleted={() => setShown(null)} />}
      {gate}
    </div>
  )
}
