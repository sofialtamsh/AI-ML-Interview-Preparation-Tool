import { Fragment, type ReactNode } from 'react'

/** Renders the content format's tiny markdown subset (**bold** and `code`) as React nodes:
 * no HTML is ever injected, so content can't run scripts. */
export function RichText({ text }: { text: string }) {
  const parts: ReactNode[] = []
  const pattern = /\*\*(.+?)\*\*|`([^`]+)`/g
  let last = 0
  let match: RegExpExecArray | null
  while ((match = pattern.exec(text)) !== null) {
    if (match.index > last) parts.push(text.slice(last, match.index))
    if (match[1] !== undefined) {
      parts.push(
        <strong key={match.index} className="font-semibold text-slate-900">
          {match[1]}
        </strong>,
      )
    } else {
      parts.push(
        <code key={match.index} className="rounded bg-slate-100 px-1 py-0.5 font-mono text-[0.9em] text-brand-800">
          {match[2]}
        </code>,
      )
    }
    last = match.index + match[0].length
  }
  if (last < text.length) parts.push(text.slice(last))
  return <>{parts.map((part, i) => <Fragment key={i}>{part}</Fragment>)}</>
}
