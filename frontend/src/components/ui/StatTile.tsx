import type { ReactNode } from 'react'

import { Card } from './Feedback'

export function StatTile({ label, value, note }: { label: string; value: string; note?: ReactNode }) {
  return (
    <Card className="p-5">
      <p className="text-sm font-medium text-slate-500">{label}</p>
      <p className="mt-2 font-sans text-3xl font-semibold tracking-tight text-slate-900 tabular-nums">
        {value}
      </p>
      {note && <p className="mt-1 text-xs text-slate-500">{note}</p>}
    </Card>
  )
}
