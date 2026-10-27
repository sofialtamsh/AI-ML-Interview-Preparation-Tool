import { ChevronLeft, ChevronRight } from 'lucide-react'

import { Button } from './ui/Button'

export function Pagination({
  page,
  pageSize,
  total,
  onPage,
}: {
  page: number
  pageSize: number
  total: number
  onPage: (page: number) => void
}) {
  const pages = Math.max(1, Math.ceil(total / pageSize))
  if (total === 0) return null
  const first = (page - 1) * pageSize + 1
  const last = Math.min(total, page * pageSize)
  return (
    <div className="flex items-center justify-between gap-3 border-t border-slate-100 px-5 py-3 text-sm text-slate-600">
      <p>
        <span className="font-medium text-slate-900 tabular-nums">
          {first}–{last}
        </span>{' '}
        of <span className="font-medium text-slate-900 tabular-nums">{total}</span>
      </p>
      <div className="flex gap-2">
        <Button
          variant="secondary"
          size="sm"
          disabled={page <= 1}
          onClick={() => onPage(page - 1)}
          icon={<ChevronLeft className="size-4" />}
        >
          Previous
        </Button>
        <Button variant="secondary" size="sm" disabled={page >= pages} onClick={() => onPage(page + 1)}>
          Next
          <ChevronRight className="size-4" />
        </Button>
      </div>
    </div>
  )
}
