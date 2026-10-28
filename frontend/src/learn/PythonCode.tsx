import type { ReactNode } from 'react'

const KEYWORDS = new Set(
  'False None True and as assert async await break class continue def del elif else except finally for from global if import in is lambda nonlocal not or pass raise return try while with yield'.split(' '),
)
const BUILTINS = new Set('print range len list dict set tuple int float str round zip enumerate sum min max abs sorted map filter isinstance'.split(' '))

// Order matters: comments and strings first, so keywords inside them are left alone.
const TOKEN = /(#[^\n]*)|([rbfRBF]{0,2}"""[\s\S]*?"""|[rbfRBF]{0,2}'''[\s\S]*?'''|[rbfRBF]{0,2}"(?:\\.|[^"\\\n])*"|[rbfRBF]{0,2}'(?:\\.|[^'\\\n])*')|(\b\d+(?:\.\d+)?(?:e-?\d+)?\b)|([A-Za-z_]\w*)/g

/** A tiny, safe Python highlighter: text only, no HTML injection. */
export function PythonCode({ code }: { code: string }) {
  const parts: ReactNode[] = []
  let last = 0
  for (const match of code.matchAll(TOKEN)) {
    const at = match.index ?? 0
    if (at > last) parts.push(code.slice(last, at))
    const [text, comment, string, number, word] = match
    const key = at
    if (comment) parts.push(<span key={key} className="text-slate-400 italic">{text}</span>)
    else if (string) parts.push(<span key={key} className="text-emerald-300">{text}</span>)
    else if (number) parts.push(<span key={key} className="text-amber-300">{text}</span>)
    else if (word && KEYWORDS.has(word)) parts.push(<span key={key} className="text-fuchsia-300">{text}</span>)
    else if (word && BUILTINS.has(word)) parts.push(<span key={key} className="text-sky-300">{text}</span>)
    else parts.push(text)
    last = at + text.length
  }
  if (last < code.length) parts.push(code.slice(last))
  return (
    <pre className="overflow-x-auto rounded-2xl bg-slate-950 p-4 font-mono text-[13px] leading-relaxed text-slate-100">
      <code>{parts}</code>
    </pre>
  )
}
