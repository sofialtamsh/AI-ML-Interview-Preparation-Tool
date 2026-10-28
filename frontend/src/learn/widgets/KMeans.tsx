import { Dices, Pause, Play, RotateCcw, Shuffle, StepForward } from 'lucide-react'
import { useEffect, useMemo, useReducer, useState } from 'react'

import { Button } from '../../components/ui/Button'
import { GRID, INK, MUTED, SERIES, fmt, linear, rng, type Point } from '../viz'
import { ButtonRow, Hint, Readouts, Slider, Toggle, WidgetFrame } from './controls'
import { assignClusters, bestInertia, inertia, makeBlobs, randomStarts, updateCentroids } from './ml'

const W = 400
const H = 300
const X = linear([0, 10], [0, W])
const Y = linear([0, 7.5], [H, 0])
const UNASSIGNED = '#94a3b8'

type State = {
  points: Point[]
  starts: Point[]
  centroids: Point[]
  labels: number[] | null
  phase: 'assign' | 'update'
  iterations: number
  converged: boolean
  trail: Point[][]
}

type Action = { type: 'step' } | { type: 'reset'; points?: Point[]; starts?: Point[] }

function fresh(points: Point[], starts: Point[]): State {
  return {
    points,
    starts,
    centroids: starts,
    labels: null,
    phase: 'assign',
    iterations: 0,
    converged: false,
    trail: starts.map((s) => [s]),
  }
}

function reducer(state: State, action: Action): State {
  if (action.type === 'reset') return fresh(action.points ?? state.points, action.starts ?? state.starts)
  if (state.converged) return state
  if (state.phase === 'assign') {
    const labels = assignClusters(state.points, state.centroids)
    const unchanged = state.labels !== null && labels.every((label, i) => label === state.labels![i])
    return unchanged ? { ...state, converged: true } : { ...state, labels, phase: 'update' }
  }
  const centroids = updateCentroids(state.points, state.labels!, state.centroids)
  return {
    ...state,
    centroids,
    phase: 'assign',
    iterations: state.iterations + 1,
    trail: state.trail.map((path, i) => [...path, centroids[i]]),
  }
}

const cross = 'M-7 0 H7 M0 -7 V7'

export function KMeans() {
  const [blobs, setBlobs] = useState(3)
  const [dataSeed, setDataSeed] = useState(5)
  const [k, setK] = useState(3)
  const [startSeed, setStartSeed] = useState(1)
  const [running, setRunning] = useState(false)
  const [showElbow, setShowElbow] = useState(false)
  const [state, dispatch] = useReducer(reducer, undefined, () => {
    const points = makeBlobs(3, 40, 5)
    return fresh(points, randomStarts(points, 3, rng(1)))
  })

  const restart = (opts: { blobs?: number; dataSeed?: number; k?: number; startSeed?: number }) => {
    const nb = opts.blobs ?? blobs
    const ds = opts.dataSeed ?? dataSeed
    const nk = opts.k ?? k
    const ss = opts.startSeed ?? startSeed
    setBlobs(nb)
    setDataSeed(ds)
    setK(nk)
    setStartSeed(ss)
    setRunning(false)
    const points = opts.blobs !== undefined || opts.dataSeed !== undefined ? makeBlobs(nb, 40, ds) : state.points
    dispatch({ type: 'reset', points, starts: randomStarts(points, nk, rng(ss * 7919 + nk)) })
  }

  useEffect(() => {
    if (!running) return
    if (state.converged) {
      setRunning(false)
      return
    }
    const timer = window.setTimeout(() => dispatch({ type: 'step' }), 450)
    return () => window.clearTimeout(timer)
  }, [running, state])

  const elbow = useMemo(
    () => (showElbow ? Array.from({ length: 8 }, (_, i) => bestInertia(state.points, i + 1, 11)) : []),
    [showElbow, state.points],
  )

  const { points, centroids, labels, phase, converged } = state
  const currentInertia = labels ? inertia(points, labels, centroids) : null
  const status = converged
    ? 'Converged ✓ No point changed cluster, so k-means stops.'
    : phase === 'assign'
      ? 'Next step: each point joins its nearest centroid.'
      : 'Next step: each centroid moves to the middle of its points.'

  const plot = (
    <svg viewBox={`0 0 ${W} ${H}`} className="block w-full select-none" role="img" aria-label={`k-means with k = ${k}: ${status}`}>
      {labels && phase === 'update' && !converged && (
        <g strokeOpacity="0.25" strokeWidth="1">
          {points.map((p, i) => (
            <line key={i} x1={X(p.x)} y1={Y(p.y)} x2={X(centroids[labels[i]].x)} y2={Y(centroids[labels[i]].y)} stroke={SERIES[labels[i]]} />
          ))}
        </g>
      )}
      {points.map((p, i) => (
        <circle
          key={i}
          cx={X(p.x)}
          cy={Y(p.y)}
          r="4.5"
          fill={labels ? SERIES[labels[i]] : UNASSIGNED}
          stroke="white"
          strokeWidth="1.5"
          style={{ transition: 'fill 0.3s' }}
        />
      ))}
      {state.trail.map((path, i) => (
        <polyline
          key={`t${i}`}
          points={path.map((c) => `${X(c.x)},${Y(c.y)}`).join(' ')}
          fill="none"
          stroke={SERIES[i]}
          strokeWidth="2"
          strokeDasharray="3 3"
        />
      ))}
      {centroids.map((c, i) => (
        <g key={`c${i}`} style={{ transform: `translate(${X(c.x)}px, ${Y(c.y)}px)`, transition: 'transform 0.35s ease-out' }}>
          <circle r="11" fill="white" stroke={INK} strokeWidth="1.5" />
          <path d={cross} stroke={SERIES[i]} strokeWidth="3.5" strokeLinecap="round" />
        </g>
      ))}
    </svg>
  )

  return (
    <WidgetFrame
      plot={plot}
      below={
        <>
          <p className="px-1 text-sm text-slate-700" aria-live="polite">
            {status}
          </p>
          {showElbow && <ElbowChart values={elbow} k={k} />}
        </>
      }
      controls={
        <>
          <Slider label="k (clusters to find)" value={k} min={1} max={6} onChange={(value) => restart({ k: value })} />
          <ButtonRow>
            <Button size="sm" icon={<StepForward className="size-4" />} onClick={() => dispatch({ type: 'step' })} disabled={converged || running}>
              Step
            </Button>
            <Button
              size="sm"
              variant="secondary"
              icon={running ? <Pause className="size-4" /> : <Play className="size-4" />}
              onClick={() => setRunning((r) => !r)}
              disabled={converged}
            >
              {running ? 'Pause' : 'Run'}
            </Button>
            <Button
              size="sm"
              variant="secondary"
              icon={<RotateCcw className="size-4" />}
              onClick={() => {
                setRunning(false)
                dispatch({ type: 'reset' })
              }}
            >
              Reset
            </Button>
          </ButtonRow>
          <Readouts
            items={[
              { label: 'Iterations', value: state.iterations },
              { label: 'Inertia', value: currentInertia === null ? '—' : fmt(currentInertia, 1), note: 'sum of squared distances' },
            ]}
          />
          <Button size="sm" variant="secondary" className="w-full" icon={<Dices className="size-4" />} onClick={() => restart({ startSeed: startSeed + 1 })}>
            New starting points
          </Button>
          <div className="space-y-3 border-t border-slate-200 pt-3">
            <Slider label="Blobs in new data" value={blobs} min={2} max={5} onChange={(value) => restart({ blobs: value, dataSeed: dataSeed + 1 })} />
            <Button size="sm" variant="secondary" className="w-full" icon={<Shuffle className="size-4" />} onClick={() => restart({ dataSeed: dataSeed + 1 })}>
              New data
            </Button>
          </div>
          <Toggle label="Show elbow chart" checked={showElbow} onChange={setShowElbow} />
          <Hint>Crosses are centroids; dashed lines show where they travelled.</Hint>
        </>
      }
    />
  )
}

/** Best inertia for k = 1..8: the "elbow" is where the drop flattens. */
function ElbowChart({ values, k }: { values: number[]; k: number }) {
  const w = 400
  const h = 170
  const left = 44
  const bottom = 30
  const max = Math.max(...values, 1)
  const x = linear([1, 8], [left, w - 14])
  const y = linear([0, max], [h - bottom, 12])
  const [hover, setHover] = useState<number | null>(null)
  const shown = hover ?? k
  return (
    <figure className="rounded-2xl bg-white p-3 ring-1 ring-slate-200">
      <figcaption className="flex flex-wrap justify-between gap-2 text-sm">
        <span className="font-semibold text-slate-900">Elbow chart: inertia for each k</span>
        <span className="text-slate-600">
          k = {shown}: <span className="font-mono tabular-nums">{fmt(values[shown - 1] ?? 0, 1)}</span>
        </span>
      </figcaption>
      <svg viewBox={`0 0 ${w} ${h}`} className="mx-auto mt-1 block w-full max-w-xl" role="img" aria-label="Inertia for k from 1 to 8" onPointerLeave={() => setHover(null)}>
        {[0, 0.5, 1].map((t) => (
          <g key={t}>
            <line x1={left} x2={w - 14} y1={y(max * t)} y2={y(max * t)} stroke={GRID} />
            <text x={left - 6} y={y(max * t) + 3} textAnchor="end" fontSize="10" fill={MUTED}>
              {Math.round(max * t)}
            </text>
          </g>
        ))}
        <polyline points={values.map((v, i) => `${x(i + 1)},${y(v)}`).join(' ')} fill="none" stroke={SERIES[0]} strokeWidth="2" />
        {values.map((v, i) => (
          <g key={i} onPointerEnter={() => setHover(i + 1)}>
            <rect x={x(i + 1) - 20} y={0} width={40} height={h} fill="transparent" />
            <circle cx={x(i + 1)} cy={y(v)} r={i + 1 === shown ? 6 : 4} fill={SERIES[0]} stroke="white" strokeWidth="2" />
            <text x={x(i + 1)} y={h - 10} textAnchor="middle" fontSize="11" fontWeight={i + 1 === k ? 700 : 400} fill={i + 1 === k ? INK : MUTED}>
              {i + 1}
            </text>
          </g>
        ))}
      </svg>
    </figure>
  )
}
