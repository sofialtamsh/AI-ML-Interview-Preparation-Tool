import { GraduationCap, Plus, Search, SearchX } from 'lucide-react'
import { useEffect, useState, type FormEvent } from 'react'
import { Link, useNavigate, useSearchParams } from 'react-router'

import { Pagination } from '../../components/Pagination'
import { Button } from '../../components/ui/Button'
import { Dialog } from '../../components/ui/Dialog'
import { Alert, Card, EmptyState, PageHeader, Skeleton } from '../../components/ui/Feedback'
import { SelectField, TextField } from '../../components/ui/Field'
import { useToast } from '../../components/ui/Toast'
import { errorMessage } from '../../lib/api'
import { cn } from '../../lib/cn'
import { formatDate, timeAgo } from '../../lib/format'
import type { StudentStatus } from '../../lib/types'
import { useCan, useCohorts, useCreateCohort, useStudents, type StudentFilters } from '../api'
import { StatusBadge } from '../StatusBadge'

const PAGE_SIZE = 20

function NewCohortDialog({ open, onClose }: { open: boolean; onClose: () => void }) {
  const [name, setName] = useState('')
  const [description, setDescription] = useState('')
  const create = useCreateCohort()
  const toast = useToast()

  const close = () => {
    setName('')
    setDescription('')
    create.reset()
    onClose()
  }

  const submit = (event: FormEvent) => {
    event.preventDefault()
    create.mutate(
      { name: name.trim(), description: description.trim() },
      {
        onSuccess: (cohort) => {
          toast.success(`Cohort "${cohort.name}" created`)
          close()
        },
      },
    )
  }

  return (
    <Dialog
      open={open}
      onClose={close}
      title="New cohort"
      description="Group students into a batch or learning group."
    >
      <form id="new-cohort" onSubmit={submit} className="space-y-4">
        {create.isError && <Alert>{errorMessage(create.error)}</Alert>}
        <TextField
          label="Name"
          placeholder="e.g. Batch 2026-A"
          value={name}
          onChange={(e) => setName(e.target.value)}
          autoFocus
        />
        <TextField
          label="Description"
          placeholder="Optional"
          value={description}
          onChange={(e) => setDescription(e.target.value)}
        />
        <div className="flex justify-end gap-2 pt-2">
          <Button variant="secondary" onClick={close}>
            Cancel
          </Button>
          <Button type="submit" loading={create.isPending} disabled={name.trim().length < 2}>
            Create cohort
          </Button>
        </div>
      </form>
    </Dialog>
  )
}

export default function StudentsPage() {
  const [params, setParams] = useSearchParams()
  const filters: StudentFilters = {
    q: params.get('q') ?? '',
    status: (params.get('status') as StudentStatus | null) ?? '',
    cohort_id: params.get('cohort') ?? '',
    page: Math.max(1, Number(params.get('page')) || 1),
  }
  const [search, setSearch] = useState(filters.q)
  const [cohortOpen, setCohortOpen] = useState(false)
  const students = useStudents(filters, PAGE_SIZE)
  const cohorts = useCohorts()
  const canManage = useCan('students.manage')
  const navigate = useNavigate()

  const update = (changes: Partial<Record<'q' | 'status' | 'cohort' | 'page', string>>) => {
    setParams(
      (current) => {
        const next = new URLSearchParams(current)
        for (const [key, value] of Object.entries(changes)) {
          if (value) next.set(key, value)
          else next.delete(key)
        }
        if (!('page' in changes)) next.delete('page')
        return next
      },
      { replace: true },
    )
  }

  // Debounced search keeps typing smooth and avoids a request per keystroke.
  useEffect(() => {
    if (search === filters.q) return
    const timer = window.setTimeout(() => update({ q: search }), 300)
    return () => window.clearTimeout(timer)
  }, [search]) // only re-run on typing; `update` reads the latest params itself

  const filtered = !!(filters.q || filters.status || filters.cohort_id)

  return (
    <div>
      <PageHeader
        title="Students"
        description="Every registered student, their status and cohort."
        actions={
          canManage && (
            <Button
              variant="secondary"
              icon={<Plus className="size-4" />}
              onClick={() => setCohortOpen(true)}
            >
              New cohort
            </Button>
          )
        }
      />

      <div className="mb-4 flex flex-col gap-3 sm:flex-row">
        <div className="relative flex-1">
          <Search
            className="pointer-events-none absolute top-1/2 left-3.5 size-4 -translate-y-1/2 text-slate-400"
            aria-hidden
          />
          <input
            type="search"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Search by name, email or student ID"
            aria-label="Search students"
            className="block w-full rounded-xl border-0 bg-white py-2.5 pr-3.5 pl-10 text-sm shadow-xs ring-1 ring-slate-300 ring-inset placeholder:text-slate-400 focus:ring-2 focus:ring-brand-500 focus:outline-none"
          />
        </div>
        <div className="grid grid-cols-2 gap-3 sm:w-96">
          <SelectField
            label="Status"
            hideLabel
            value={filters.status}
            onChange={(e) => update({ status: e.target.value })}
          >
            <option value="">All statuses</option>
            <option value="active">Active</option>
            <option value="suspended">Suspended</option>
            <option value="deactivated">Deactivated</option>
          </SelectField>
          <SelectField
            label="Cohort"
            hideLabel
            value={filters.cohort_id}
            onChange={(e) => update({ cohort: e.target.value })}
          >
            <option value="">All cohorts</option>
            {cohorts.data?.map((c) => (
              <option key={c.id} value={c.id}>
                {c.name} ({c.student_count})
              </option>
            ))}
          </SelectField>
        </div>
      </div>

      <Card className="overflow-hidden">
        {students.isPending ? (
          <div className="space-y-3 p-5">
            {[0, 1, 2, 3, 4].map((i) => (
              <Skeleton key={i} className="h-11" />
            ))}
          </div>
        ) : students.isError ? (
          <div className="p-5">
            <Alert>{errorMessage(students.error)}</Alert>
          </div>
        ) : students.data.total === 0 ? (
          filtered ? (
            <EmptyState
              icon={<SearchX className="size-6" />}
              title="No students match these filters"
              action={
                <Button
                  variant="secondary"
                  onClick={() => {
                    setSearch('')
                    setParams({}, { replace: true })
                  }}
                >
                  Clear filters
                </Button>
              }
            />
          ) : (
            <EmptyState icon={<GraduationCap className="size-6" />} title="No students yet">
              Students appear here as soon as they register.
            </EmptyState>
          )
        ) : (
          <>
            <div
              className={cn(
                'overflow-x-auto transition-opacity',
                students.isPlaceholderData && 'opacity-60',
              )}
            >
              <table className="w-full min-w-[720px] text-left text-sm">
                <thead className="border-b border-slate-100 bg-slate-50/80 text-xs text-slate-500">
                  <tr>
                    <th className="px-5 py-3 font-medium">Student</th>
                    <th className="px-3 py-3 font-medium">ID</th>
                    <th className="px-3 py-3 font-medium">Cohort</th>
                    <th className="px-3 py-3 font-medium">Status</th>
                    <th className="px-3 py-3 font-medium">Joined</th>
                    <th className="px-5 py-3 font-medium">Last sign-in</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100">
                  {students.data.items.map((s) => (
                    <tr
                      key={s.id}
                      onClick={() => navigate(`/admin/students/${s.id}`)}
                      className="cursor-pointer transition hover:bg-brand-50/40"
                    >
                      <td className="px-5 py-3">
                        <Link
                          to={`/admin/students/${s.id}`}
                          className="font-medium text-slate-900 hover:text-brand-700"
                          onClick={(e) => e.stopPropagation()}
                        >
                          {s.full_name}
                        </Link>
                        <p className="text-xs text-slate-500">{s.email}</p>
                      </td>
                      <td className="px-3 py-3 font-mono text-xs text-slate-600">{s.student_code}</td>
                      <td className="px-3 py-3 text-slate-600">{s.cohort?.name ?? '—'}</td>
                      <td className="px-3 py-3">
                        <StatusBadge status={s.status} />
                      </td>
                      <td className="px-3 py-3 text-slate-600">{formatDate(s.created_at)}</td>
                      <td className="px-5 py-3 text-slate-600">{timeAgo(s.last_login_at)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            <Pagination
              page={students.data.page}
              pageSize={PAGE_SIZE}
              total={students.data.total}
              onPage={(page) => update({ page: String(page) })}
            />
          </>
        )}
      </Card>

      {canManage && <NewCohortDialog open={cohortOpen} onClose={() => setCohortOpen(false)} />}
    </div>
  )
}
