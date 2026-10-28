import type { ReactNode } from 'react'

import type { RevisionContent } from '../../lib/types'
import { RichText } from '../RichText'

function Block({ title, children, className }: { title: string; children: ReactNode; className?: string }) {
  return (
    <section className={`rounded-3xl bg-white p-5 ring-1 ring-slate-200 ${className ?? ''}`}>
      <h3 className="font-display text-lg font-bold text-slate-900">{title}</h3>
      <div className="mt-3">{children}</div>
    </section>
  )
}

export function RevisionSheet({ revision }: { revision: RevisionContent }) {
  return (
    <div className="grid gap-4 lg:grid-cols-2">
      <Block title="📖 Definitions" className="lg:col-span-2">
        <dl className="grid gap-2 sm:grid-cols-2">
          {revision.definitions.map((d) => (
            <div key={d.term} className="rounded-2xl bg-slate-50 px-4 py-3">
              <dt className="font-semibold text-slate-900">{d.term}</dt>
              <dd className="text-sm text-slate-600">
                <RichText text={d.meaning} />
              </dd>
            </div>
          ))}
        </dl>
      </Block>

      {revision.formulas.length > 0 && (
        <Block title="🧮 Formulas" className="lg:col-span-2">
          <ul className="grid gap-2 sm:grid-cols-2">
            {revision.formulas.map((f) => (
              <li key={f.name} className="rounded-2xl bg-slate-50 p-4">
                <p className="text-xs font-bold tracking-wide text-slate-500 uppercase">{f.name}</p>
                <p className="mt-1 overflow-x-auto font-mono text-base whitespace-nowrap text-slate-900">{f.expression}</p>
                <p className="mt-1 text-sm text-slate-600">
                  <RichText text={f.meaning} />
                </p>
              </li>
            ))}
          </ul>
        </Block>
      )}

      {revision.comparison && (
        <Block title={`⚖️ ${revision.comparison.title}`} className="lg:col-span-2">
          <div className="overflow-x-auto">
            <table className="w-full min-w-[32rem] text-left text-sm">
              <thead>
                <tr>
                  {revision.comparison.columns.map((c, i) => (
                    <th key={i} scope="col" className="border-b border-slate-200 px-3 py-2 font-semibold text-slate-900">
                      {c}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {revision.comparison.rows.map((row, r) => (
                  <tr key={r} className="even:bg-slate-50">
                    {row.map((cell, c) =>
                      c === 0 ? (
                        <th key={c} scope="row" className="px-3 py-2 font-semibold text-slate-800">
                          <RichText text={cell} />
                        </th>
                      ) : (
                        <td key={c} className="px-3 py-2 text-slate-700">
                          <RichText text={cell} />
                        </td>
                      ),
                    )}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </Block>
      )}

      <Block title="🚫 Common mistakes">
        <ul className="space-y-2 text-slate-700">
          {revision.mistakes.map((m, i) => (
            <li key={i} className="flex gap-2">
              <span aria-hidden>✗</span>
              <span>
                <RichText text={m} />
              </span>
            </li>
          ))}
        </ul>
      </Block>

      {revision.confusions.length > 0 && (
        <Block title="🤔 Don't mix these up">
          <ul className="space-y-3">
            {revision.confusions.map((c) => (
              <li key={c.pair}>
                <p className="font-semibold text-slate-900">{c.pair}</p>
                <p className="text-sm text-slate-600">
                  <RichText text={c.difference} />
                </p>
              </li>
            ))}
          </ul>
        </Block>
      )}

      <section className="rounded-3xl bg-gradient-to-br from-emerald-500 to-brand-600 p-5 text-white lg:col-span-2">
        <h3 className="font-display text-lg font-bold">✅ Takeaways</h3>
        <ul className="mt-2 space-y-1.5">
          {revision.takeaways.map((t, i) => (
            <li key={i} className="flex gap-2">
              <span aria-hidden>→</span>
              <span>
                <RichText text={t} />
              </span>
            </li>
          ))}
        </ul>
      </section>
    </div>
  )
}
