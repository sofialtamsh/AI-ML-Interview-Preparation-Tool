import { CircleCheck, CircleX, GitCompareArrows } from 'lucide-react'
import { useState } from 'react'

import { Alert, Badge, Card, CardHeader, Skeleton } from '../../components/ui/Feedback'
import { StatTile } from '../../components/ui/StatTile'
import { MasteryChip, ProgressBar } from '../../learn/progress'
import { SECTIONS, type ComponentKey } from '../../learn/sections'
import { errorMessage } from '../../lib/api'
import { cn } from '../../lib/cn'
import { formatDateTime, formatDuration, timeAgo } from '../../lib/format'
import type { StudentLearning } from '../../lib/types'
import { useStudentLearning } from '../api'

type Attempt = StudentLearning['quiz_attempts'][number]

const minutes = (seconds: number | null) => (seconds === null ? '—' : `${Math.max(1, Math.round(seconds / 60))} min`)

/** Two attempts at the same quiz, question by question. */
function Comparison({ first, second }: { first: Attempt; second: Attempt }) {
  const [older, newer] = first.submitted_at < second.submitted_at ? [first, second] : [second, first]
  return (
    <div className="overflow-x-auto">
      <table className="w-full min-w-[32rem] text-sm" aria-label="Attempt comparison">
        <thead className="text-left text-xs text-slate-500">
          <tr>
            <th scope="col" className="py-2 pr-3 font-medium">
              Question
            </th>
            <th scope="col" className="px-3 py-2 font-medium">
              Attempt {older.attempt_number} ({Math.round(older.score_pct)}%)
            </th>
            <th scope="col" className="px-3 py-2 font-medium">
              Attempt {newer.attempt_number} ({Math.round(newer.score_pct)}%)
            </th>
          </tr>
        </thead>
        <tbody className="divide-y divide-slate-100">
          {older.responses.map((response, i) => {
            const later = newer.responses[i]
            const mark = (correct: boolean | undefined) =>
              correct === undefined ? (
                '—'
              ) : correct ? (
                <CircleCheck className="size-4 text-emerald-600" aria-label="Correct" />
              ) : (
                <CircleX className="size-4 text-rose-600" aria-label="Wrong" />
              )
            return (
              <tr key={i}>
                <td className="py-2 pr-3 text-slate-800">
                  <span className="mr-1 text-xs text-slate-400">Q{i + 1}</span>
                  {response.prompt}
                </td>
                <td className="px-3 py-2">{mark(response.correct)}</td>
                <td className="px-3 py-2">{mark(later?.correct)}</td>
              </tr>
            )
          })}
        </tbody>
      </table>
    </div>
  )
}

function QuizHistory({ attempts }: { attempts: Attempt[] }) {
  const [picked, setPicked] = useState<string[]>([])
  const chosen = attempts.filter((a) => picked.includes(a.id))
  const sameTopic = chosen.length === 2 && chosen[0].topic === chosen[1].topic
  const toggle = (id: string) => setPicked((current) => (current.includes(id) ? current.filter((x) => x !== id) : [...current.slice(-1), id]))

  return (
    <Card className="overflow-hidden">
      <CardHeader title="Quiz attempts" description="Every attempt is kept. Tick two attempts of the same quiz to compare them." />
      {attempts.length === 0 ? (
        <p className="px-5 pb-5 text-sm text-slate-600">No quiz attempts yet.</p>
      ) : (
        <>
          <ul className="divide-y divide-slate-100">
            {attempts.map((attempt) => (
              <li key={attempt.id} className="flex items-center gap-3 px-5 py-2.5 text-sm">
                <input
                  type="checkbox"
                  className="size-4 accent-brand-600"
                  checked={picked.includes(attempt.id)}
                  onChange={() => toggle(attempt.id)}
                  aria-label={`Compare ${attempt.topic} attempt ${attempt.attempt_number}`}
                />
                <span
                  className={cn(
                    'w-14 rounded-full px-2 py-0.5 text-center text-xs font-bold tabular-nums',
                    attempt.score_pct >= 75 ? 'bg-emerald-100 text-emerald-800' : attempt.score_pct >= 50 ? 'bg-sky-100 text-sky-800' : 'bg-amber-100 text-amber-900',
                  )}
                >
                  {Math.round(attempt.score_pct)}%
                </span>
                <span className="min-w-0 flex-1">
                  <span className="font-medium text-slate-900">{attempt.topic}</span>
                  <span className="text-slate-500">
                    {' '}
                    · attempt {attempt.attempt_number} · {attempt.correct}/{attempt.total} · {minutes(attempt.duration_seconds)}
                  </span>
                </span>
                <time className="text-xs text-slate-500" dateTime={attempt.submitted_at}>
                  {formatDateTime(attempt.submitted_at)}
                </time>
              </li>
            ))}
          </ul>
          {chosen.length === 2 && (
            <div className="border-t border-slate-100 p-5">
              <p className="mb-3 flex items-center gap-2 text-sm font-semibold text-slate-900">
                <GitCompareArrows className="size-4" aria-hidden /> Comparing two attempts
              </p>
              {sameTopic ? <Comparison first={chosen[0]} second={chosen[1]} /> : <Alert tone="info">Pick two attempts of the same topic&apos;s quiz.</Alert>}
            </div>
          )}
        </>
      )}
    </Card>
  )
}

/** Everything about a student's learning, for their admin profile. */
export function StudentLearningPanel({ studentId }: { studentId: string }) {
  const learning = useStudentLearning(studentId)
  if (learning.isPending) return <Skeleton className="h-64 rounded-2xl" />
  if (learning.isError) return <Alert>{errorMessage(learning.error)}</Alert>
  const { summary, quiz_attempts, practice, timeline } = learning.data

  return (
    <div className="space-y-6">
      <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 xl:grid-cols-5">
        <StatTile label="Path completed" value={`${summary.overall_completion}%`} note={`${summary.topics_completed} of ${summary.topics.length} topics complete`} />
        <StatTile
          label="Quiz average"
          value={summary.quiz_average !== null ? `${Math.round(summary.quiz_average)}%` : '—'}
          note={`${quiz_attempts.length} attempt(s)`}
        />
        <StatTile
          label="Interview practice"
          value={summary.interview.average_score !== null ? `${summary.interview.average_score.toFixed(1)}/10` : '—'}
          note={`${summary.interview.answers_recorded} recorded · ${summary.interview.feedback_count} scored`}
        />
        <StatTile
          label="Time learning"
          value={formatDuration(summary.activity.learning_seconds)}
          note={`${formatDuration(summary.activity.learning_seconds_last_7)} in the last 7 days`}
        />
        <StatTile
          label="Active days (30)"
          value={String(summary.activity.active_days_last_30)}
          note={summary.activity.last_active_at ? `Last active ${timeAgo(summary.activity.last_active_at).toLowerCase()}` : 'No learning yet'}
        />
      </div>

      <Card className="overflow-hidden">
        <CardHeader
          title="Topic progress"
          description="Completion is the sections the student went through; mastery comes from their recent quizzes and interview practice."
        />
        <div className="overflow-x-auto">
          <table className="w-full min-w-[44rem] text-left text-sm">
            <thead className="bg-slate-50 text-xs text-slate-500">
              <tr>
                <th scope="col" className="px-5 py-2 font-medium">
                  Topic
                </th>
                <th scope="col" className="px-3 py-2 font-medium">
                  Completion
                </th>
                <th scope="col" className="px-3 py-2 font-medium">
                  Mastery
                </th>
                <th scope="col" className="px-3 py-2 font-medium">
                  Quiz best / last
                </th>
                <th scope="col" className="px-3 py-2 font-medium">
                  Time
                </th>
                <th scope="col" className="px-5 py-2 font-medium">
                  Last visit
                </th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {summary.topics.map((topic) => (
                <tr key={topic.slug}>
                  <td className="px-5 py-2.5">
                    <span className="font-medium text-slate-900">{topic.name}</span>
                    <span className="block text-xs text-slate-500">
                      {Object.entries(topic.sections)
                        .filter(([, status]) => status === 'done')
                        .map(([section]) => SECTIONS[section as ComponentKey]?.label)
                        .join(', ') || 'No sections done'}
                    </span>
                  </td>
                  <td className="w-40 px-3 py-2.5">
                    <ProgressBar value={topic.completion} label={`${topic.name} completion`} />
                    <span className="text-xs text-slate-500 tabular-nums">
                      {topic.done}/{topic.total}
                    </span>
                  </td>
                  <td className="px-3 py-2.5">
                    <MasteryChip band={topic.mastery.band} />
                  </td>
                  <td className="px-3 py-2.5 text-slate-700 tabular-nums">
                    {topic.quiz_best !== null ? `${Math.round(topic.quiz_best)}% / ${Math.round(topic.quiz_last ?? 0)}%` : '—'}
                  </td>
                  <td className="px-3 py-2.5 text-slate-700 tabular-nums">{topic.active_seconds ? formatDuration(topic.active_seconds) : '—'}</td>
                  <td className="px-5 py-2.5 text-slate-600">{timeAgo(topic.last_visited_at)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        {(summary.strengths.length > 0 || summary.weaknesses.length > 0) && (
          <p className="border-t border-slate-100 px-5 py-3 text-sm text-slate-700">
            {summary.strengths.length > 0 && (
              <>
                <span className="font-semibold text-emerald-700">Strong:</span> {summary.strengths.join(', ')}.{' '}
              </>
            )}
            {summary.weaknesses.length > 0 && (
              <>
                <span className="font-semibold text-amber-800">Needs work:</span> {summary.weaknesses.join(', ')}.
              </>
            )}
          </p>
        )}
      </Card>

      <QuizHistory attempts={quiz_attempts} />

      <div className="grid gap-6 lg:grid-cols-2">
        <Card className="overflow-hidden">
          <CardHeader title="Interview practice" description="Scores only; recordings never reach the server and transcripts stay private." />
          {practice.length === 0 ? (
            <p className="px-5 pb-5 text-sm text-slate-600">No scored answers yet.</p>
          ) : (
            <ul className="divide-y divide-slate-100">
              {practice.map((item, i) => (
                <li key={i} className="px-5 py-2.5 text-sm">
                  <div className="flex items-center gap-2">
                    <span className="font-semibold text-slate-900 tabular-nums">{item.score !== null ? `${item.score.toFixed(1)}/10` : 'No answer'}</span>
                    {item.verdict && <Badge>{item.verdict}</Badge>}
                    {item.deleted && <Badge>Deleted by student</Badge>}
                    <span className="ml-auto text-xs text-slate-500">{timeAgo(item.created_at)}</span>
                  </div>
                  <p className="truncate text-slate-600" title={item.question}>
                    {item.topic}: {item.question}
                  </p>
                </li>
              ))}
            </ul>
          )}
        </Card>

        <Card className="overflow-hidden">
          <CardHeader title="Recent activity" description="The latest 40 things this student did." />
          {timeline.length === 0 ? (
            <p className="px-5 pb-5 text-sm text-slate-600">No learning activity yet.</p>
          ) : (
            <ul className="max-h-96 divide-y divide-slate-100 overflow-y-auto">
              {timeline.map((entry, i) => (
                <li key={i} className="flex items-center gap-3 px-5 py-2 text-sm">
                  <span className="min-w-0 flex-1 text-slate-700">
                    {entry.action} <span className="font-medium text-slate-900">{SECTIONS[entry.section as ComponentKey]?.label ?? entry.section}</span> · {entry.topic}
                  </span>
                  <time className="shrink-0 text-xs text-slate-500" dateTime={entry.at}>
                    {timeAgo(entry.at)}
                  </time>
                </li>
              ))}
            </ul>
          )}
        </Card>
      </div>
    </div>
  )
}
