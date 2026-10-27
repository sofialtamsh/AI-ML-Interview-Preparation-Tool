import { ArrowRight, Copy, Laptop, Sparkles, UsersRound } from 'lucide-react'
import { Link } from 'react-router'

import { Card, EmptyState, Skeleton } from '../../components/ui/Feedback'
import { useToast } from '../../components/ui/Toast'
import { formatDate } from '../../lib/format'
import { useCurrentStudent, useSessions } from '../api'

function greeting(hour = new Date().getHours()) {
  if (hour < 5) return 'Burning the midnight oil'
  if (hour < 12) return 'Good morning'
  if (hour < 17) return 'Good afternoon'
  return 'Good evening'
}

export default function DashboardPage() {
  const student = useCurrentStudent()
  const sessions = useSessions()
  const toast = useToast()
  const firstName = student.full_name.split(' ')[0]

  const copyId = async () => {
    try {
      await navigator.clipboard.writeText(student.student_code)
      toast.success('Student ID copied')
    } catch {
      toast.error('Could not copy. Your ID is ' + student.student_code)
    }
  }

  return (
    <div className="space-y-6">
      <section className="relative animate-fade-up overflow-hidden rounded-3xl bg-gradient-to-br from-brand-600 via-violet-600 to-fuchsia-600 px-6 py-8 text-white shadow-xl shadow-brand-600/20 sm:px-10 sm:py-10">
        <div
          aria-hidden
          className="absolute -top-16 -right-10 size-64 animate-float rounded-full bg-white/15 blur-2xl"
        />
        <div
          aria-hidden
          className="absolute -bottom-24 left-1/3 size-72 animate-float rounded-full bg-lime-300/20 blur-3xl [animation-delay:-3s]"
        />
        <div className="relative">
          <p className="text-sm font-medium text-white/75">{greeting()},</p>
          <h1 className="mt-1 font-display text-3xl font-bold tracking-tight sm:text-4xl">
            {firstName} <span aria-hidden>👋</span>
          </h1>
          <p className="mt-3 max-w-xl text-white/85">
            This is your space to get interview-ready for AI/ML roles. Everything you do here is
            saved to your account, so you can continue on any device.
          </p>
          <button
            type="button"
            onClick={copyId}
            className="mt-6 inline-flex items-center gap-2 rounded-full bg-white/15 px-3.5 py-1.5 font-mono text-sm ring-1 ring-white/25 backdrop-blur transition hover:bg-white/25"
            aria-label={`Copy student ID ${student.student_code}`}
          >
            {student.student_code}
            <Copy className="size-3.5" aria-hidden />
          </button>
        </div>
      </section>

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
        <Card className="animate-fade-up [animation-delay:80ms] lg:col-span-2">
          <EmptyState icon={<Sparkles className="size-6" />} title="Your topics are on the way">
            Our team is preparing the first AI/ML topics. Once they're published, they'll appear
            here, and every lesson, quiz and practice question you complete will be saved to
            your account automatically.
          </EmptyState>
        </Card>

        <Card className="animate-fade-up p-5 [animation-delay:160ms]">
          <h2 className="font-display text-base font-semibold text-slate-900">Your account</h2>
          <dl className="mt-4 space-y-4 text-sm">
            <div className="flex items-center justify-between gap-3">
              <dt className="text-slate-500">Member since</dt>
              <dd className="font-medium text-slate-900">{formatDate(student.created_at)}</dd>
            </div>
            {student.cohort_name && (
              <div className="flex items-center justify-between gap-3">
                <dt className="flex items-center gap-1.5 text-slate-500">
                  <UsersRound className="size-4" aria-hidden /> Cohort
                </dt>
                <dd className="font-medium text-slate-900">{student.cohort_name}</dd>
              </div>
            )}
            <div className="flex items-center justify-between gap-3">
              <dt className="flex items-center gap-1.5 text-slate-500">
                <Laptop className="size-4" aria-hidden /> Signed-in devices
              </dt>
              <dd className="font-medium text-slate-900">
                {sessions.data ? sessions.data.length : <Skeleton className="h-4 w-6" />}
              </dd>
            </div>
          </dl>
          <Link
            to="/app/profile"
            className="group mt-6 inline-flex items-center gap-1.5 text-sm font-semibold text-brand-700 hover:text-brand-800"
          >
            Profile & devices
            <ArrowRight className="size-4 transition group-hover:translate-x-0.5" aria-hidden />
          </Link>
        </Card>
      </div>
    </div>
  )
}
