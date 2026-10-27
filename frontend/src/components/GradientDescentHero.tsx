import { useEffect, useMemo, useState } from 'react'

/**
 * A small, honest gradient-descent animation: a ball takes real GD steps on
 * f(x) = ½(x − 0.6)² + 0.08·cos(4x). The readout shows the actual step, loss and gradient.
 */

const LEARNING_RATE = 0.32
const MAX_STEPS = 16
const X_MIN = -3
const X_MAX = 3.6
const W = 400
const H = 230
const PAD = 22

const loss = (x: number) => 0.5 * (x - 0.6) ** 2 + 0.08 * Math.cos(4 * x)
const grad = (x: number) => x - 0.6 - 0.32 * Math.sin(4 * x)

const Y_MAX = Math.max(loss(X_MIN), loss(X_MAX))
const sx = (x: number) => PAD + ((x - X_MIN) / (X_MAX - X_MIN)) * (W - 2 * PAD)
const sy = (y: number) => H - PAD - (y / Y_MAX) * (H - 2 * PAD - 12)

function descend(start: number): number[] {
  const xs = [start]
  for (let i = 0; i < MAX_STEPS; i++) {
    const x = xs.at(-1)!
    const next = x - LEARNING_RATE * grad(x)
    xs.push(next)
    if (Math.abs(next - x) < 0.004) break
  }
  return xs
}

const CURVE = Array.from({ length: 121 }, (_, i) => {
  const x = X_MIN + (i / 120) * (X_MAX - X_MIN)
  return `${i ? 'L' : 'M'}${sx(x).toFixed(1)},${sy(loss(x)).toFixed(1)}`
}).join(' ')

const STARTS = [-2.7, 3.4, -1.9, 2.8]

function prefersReducedMotion() {
  return typeof window !== 'undefined' && !!window.matchMedia?.('(prefers-reduced-motion: reduce)').matches
}

export function GradientDescentHero() {
  const [run, setRun] = useState(0)
  const path = useMemo(() => descend(STARTS[run % STARTS.length]), [run])
  const [step, setStep] = useState(() => (prefersReducedMotion() ? Number.MAX_SAFE_INTEGER : 0))
  const current = Math.min(step, path.length - 1)

  useEffect(() => {
    if (prefersReducedMotion()) return
    const done = current >= path.length - 1
    const timer = window.setTimeout(
      () => {
        if (done) {
          setRun((r) => r + 1)
          setStep(0)
        } else {
          setStep((s) => s + 1)
        }
      },
      done ? 2200 : 650,
    )
    return () => window.clearTimeout(timer)
  }, [current, path.length])

  const x = path[current]
  const trail = path.slice(0, current + 1)

  return (
    <figure className="relative w-full max-w-md">
      <svg viewBox={`0 0 ${W} ${H}`} className="w-full" role="img" aria-labelledby="gd-caption">
        <defs>
          <linearGradient id="gd-curve" x1="0" x2="1">
            <stop offset="0" stopColor="#a78bfa" />
            <stop offset="1" stopColor="#f0abfc" />
          </linearGradient>
          <radialGradient id="gd-glow">
            <stop offset="0" stopColor="#bef264" stopOpacity="0.55" />
            <stop offset="1" stopColor="#bef264" stopOpacity="0" />
          </radialGradient>
        </defs>
        {[0.25, 0.5, 0.75].map((t) => (
          <line
            key={t}
            x1={PAD}
            x2={W - PAD}
            y1={PAD + t * (H - 2 * PAD)}
            y2={PAD + t * (H - 2 * PAD)}
            stroke="white"
            strokeOpacity="0.07"
          />
        ))}
        <path d={CURVE} fill="none" stroke="url(#gd-curve)" strokeWidth="2.5" strokeLinecap="round" />
        {trail.slice(0, -1).map((tx, i) => (
          <g key={`${run}-${i}`}>
            <line
              x1={sx(tx)}
              y1={sy(loss(tx))}
              x2={sx(trail[i + 1])}
              y2={sy(loss(trail[i + 1]))}
              stroke="#bef264"
              strokeOpacity="0.35"
              strokeDasharray="3 4"
            />
            <circle cx={sx(tx)} cy={sy(loss(tx))} r="3.5" fill="#e9d5ff" fillOpacity={0.35 + (0.5 * i) / trail.length} />
          </g>
        ))}
        <circle cx={sx(x)} cy={sy(loss(x)) - 1} r="18" fill="url(#gd-glow)" className="transition-all duration-500 ease-out" />
        <circle
          cx={sx(x)}
          cy={sy(loss(x)) - 1}
          r="7"
          fill="#bef264"
          stroke="#1e1b4b"
          strokeWidth="2"
          className="transition-all duration-500 ease-out"
        />
      </svg>
      <figcaption
        id="gd-caption"
        className="mt-3 flex flex-wrap gap-x-4 gap-y-1 font-mono text-xs text-violet-200/80"
      >
        <span>step {String(current).padStart(2, '0')}</span>
        <span>loss {loss(x).toFixed(3)}</span>
        <span>∇ {grad(x).toFixed(3)}</span>
        <span>η = {LEARNING_RATE}</span>
      </figcaption>
    </figure>
  )
}
