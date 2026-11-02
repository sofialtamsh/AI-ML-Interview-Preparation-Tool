import { X } from 'lucide-react'
import { useId, useState } from 'react'

import { CONTROL } from '../components/ui/Field'
import { cn } from '../lib/cn'
import { useDebounced } from '../lib/useDebounced'
import { useStudents } from './api'

export type PickedStudent = { id: string; full_name: string; student_code: string }

/** Search the student directory and pick one student (needs students.view). */
export function StudentPicker({ selected, onChange }: { selected: PickedStudent | null; onChange: (student: PickedStudent | null) => void }) {
  const id = useId()
  const [query, setQuery] = useState('')
  const [open, setOpen] = useState(false)
  const [active, setActive] = useState(0)
  const q = useDebounced(query, 250)
  const results = useStudents({ q, status: '', cohort_id: '', page: 1 }, 8, open && !selected)
  const items = results.data?.items ?? []

  if (selected) {
    return (
      <div>
        <span className="mb-1.5 block text-sm font-medium text-slate-800">Student</span>
        <div className="flex items-center gap-2 rounded-xl bg-white px-3.5 py-2 text-sm shadow-xs ring-1 ring-slate-300 ring-inset">
          <span className="min-w-0 flex-1 truncate">
            <span className="font-medium text-slate-900">{selected.full_name}</span> <span className="text-xs text-slate-500">{selected.student_code}</span>
          </span>
          <button
            type="button"
            onClick={() => onChange(null)}
            aria-label="Show all students"
            className="rounded-md p-0.5 text-slate-500 hover:bg-slate-100 hover:text-slate-900"
          >
            <X className="size-4" aria-hidden />
          </button>
        </div>
      </div>
    )
  }

  const pick = (student: PickedStudent) => {
    onChange({ id: student.id, full_name: student.full_name, student_code: student.student_code })
    setQuery('')
    setOpen(false)
  }

  return (
    <div className="relative">
      <label htmlFor={id} className="mb-1.5 block text-sm font-medium text-slate-800">
        Student
      </label>
      <input
        id={id}
        role="combobox"
        aria-expanded={open}
        aria-controls={`${id}-list`}
        aria-autocomplete="list"
        aria-activedescendant={open && items[active] ? `${id}-${items[active].id}` : undefined}
        placeholder="All students"
        autoComplete="off"
        value={query}
        className={CONTROL}
        onFocus={() => setOpen(true)}
        onBlur={() => setOpen(false)}
        onChange={(e) => {
          setQuery(e.target.value)
          setOpen(true)
          setActive(0)
        }}
        onKeyDown={(e) => {
          if (e.key === 'ArrowDown') {
            e.preventDefault()
            setOpen(true)
            setActive((i) => Math.min(i + 1, items.length - 1))
          } else if (e.key === 'ArrowUp') {
            e.preventDefault()
            setActive((i) => Math.max(i - 1, 0))
          } else if (e.key === 'Enter' && open && items[active]) {
            e.preventDefault()
            pick(items[active])
          } else if (e.key === 'Escape') {
            setOpen(false)
          }
        }}
      />
      {open && (
        <div className="absolute inset-x-0 top-full z-30 mt-1 overflow-hidden rounded-xl bg-white shadow-lg ring-1 ring-slate-200">
          {results.isPending ? (
            <p className="px-3.5 py-2 text-sm text-slate-500">Searching…</p>
          ) : items.length === 0 ? (
            <p className="px-3.5 py-2 text-sm text-slate-500">No students match.</p>
          ) : (
            <ul id={`${id}-list`} role="listbox" aria-label="Students" className="max-h-72 overflow-y-auto py-1">
              {items.map((student, i) => (
                <li
                  key={student.id}
                  id={`${id}-${student.id}`}
                  role="option"
                  aria-selected={i === active}
                  // Keep focus in the input so its blur doesn't close the list before the click.
                  onMouseDown={(e) => e.preventDefault()}
                  onClick={() => pick(student)}
                  onMouseEnter={() => setActive(i)}
                  className={cn('cursor-pointer px-3.5 py-2 text-sm', i === active && 'bg-brand-50')}
                >
                  <span className="block font-medium text-slate-900">{student.full_name}</span>
                  <span className="block truncate text-xs text-slate-500">
                    {student.student_code} · {student.email}
                  </span>
                </li>
              ))}
            </ul>
          )}
        </div>
      )}
    </div>
  )
}
