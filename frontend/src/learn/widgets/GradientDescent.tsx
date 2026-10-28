import { Pause, Play, RotateCcw, StepForward } from 'lucide-react'
import { useEffect, useState, type MouseEvent } from 'react'

import { Button } from '../../components/ui/Button'
import { GRID, INK, MUTED, SERIES, fmt, linear, svgPoint, type Point } from '../viz'
import { ButtonRow, Choice, Hint, Readouts, Slider, WidgetFrame } from './controls'
import { AT_MINIMUM, BOWL, bowlLoss, optimizerStep, startState, type OptState, type Optimizer } from './ml'

const W = 400
const H = 300
const X = linear([-5, 5], [0, W])
const Y = linear([-3.75, 3.75], [H, 0])
const PX = W / 10
const RATES = [0.001, 0.003, 0.005, 0.01, 0.02, 0.05, 0.1, 0.12, 0.15, 0.2, 0.24, 0.26, 0.3, 0.5]
const MAX_STEPS = 2000
const LEVELS = [64, 32, 16, 8, 4, 2, 1, 0.5, 0.2, 0.05]
// Sequential blue ramp, light (high loss) to dark (low loss).
const RAMP = ['#f4f8fd', '#e8f1fb', '#d9e8f8', '#c6dcf4', '#b1cfef', '#99c0ea', '#7fb0e4', '#649fde', '#4a8ed9', '#2a78d6']
const NAMES: Record<Optimizer, string> = { gd: 'Gradient descent', momentum: 'Momentum', adam: 'Adam' }
const COLOURS: Record<Optimizer, string> = { gd: SERIES[1], momentum: SERIES[2], adam: SERIES[5] }

type Run = { optimizer: Optimizer; lr: number; result: string }
type Status = 'ready' | 'running' | 'reached' | 'diverged' | 'gave_up'

export function GradientDescent() {
  const [start, setStart] = useState<Point>({ x: -4.2, y: 2.5 })
  const [optimizer, setOptimizer] = useState<Optimizer>('gd')
  const [rateIndex, setRateIndex] = useState(5)
  const [path, setPath] = useState<OptState[]>(() => [startState({ x: -4.2, y: 2.5 })])
  const [status, setStatus] = useState<Status>('ready')
  const [runs, setRuns] = useState<Run[]>([])
  const lr = RATES[rateIndex]
  const steps = path.length - 1
  const current = path[path.length - 1]
  const loss = bowlLoss(current.p)
  const done = status === 'reached' || status === 'diverged' || status === 'gave_up'

  const restart = (from = start) => {
    setPath([startState(from)])
    setStatus('ready')
  }

  const advance = (count: number) => {
    const next = [...path]
    let outcome: Status | null = null
    for (let i = 0; i < count && !outcome; i++) {
      const state = optimizerStep(next[next.length - 1], optimizer, lr)
      next.push(state)
      const value = bowlLoss(state.p)
      if (!Number.isFinite(value) || value > 1e4) outcome = 'diverged'
      else if (value < AT_MINIMUM) outcome = 'reached'
      else if (next.length - 1 >= MAX_STEPS) outcome = 'gave_up'
    }
    setPath(next)
    if (!outcome) return
    const taken = next.length - 1
    const result = outcome === 'reached' ? `${taken} steps` : outcome === 'diverged' ? `diverged at step ${taken}` : `not there after ${MAX_STEPS}`
    setStatus(outcome)
    setRuns((previous) => [{ optimizer, lr, result }, ...previous].slice(0, 5))
  }

  useEffect(() => {
    if (status !== 'running') return
    const timer = window.setInterval(() => advance(steps < 40 ? 1 : steps < 200 ? 3 : 15), 50)
    return () => window.clearInterval(timer)
  })

  const choose = (event: MouseEvent<SVGSVGElement>) => {
    const p = svgPoint(event.currentTarget, event)
    const next = { x: X.invert(p.x), y: Y.invert(p.y) }
    setStart(next)
    restart(next)
  }

  const visible = path.filter((s) => Math.abs(s.p.x) < 50 && Math.abs(s.p.y) < 50)
  const colour = COLOURS[optimizer]
  const statusText: Record<Status, string> = {
    ready: 'Tap the map to choose a start, then Step or Play.',
    running: `${NAMES[optimizer]} is rolling downhill…`,
    reached: `Reached the minimum in ${steps} steps 🎯`,
    diverged: `Diverged 💥 The steps grew until the loss exploded.`,
    gave_up: `Still not there after ${MAX_STEPS} steps: far too slow.`,
  }

  return (
    <WidgetFrame
      plot={
        <svg
          viewBox={`0 0 ${W} ${H}`}
          className="block w-full cursor-crosshair select-none"
          role="img"
          aria-label={`Loss contour map. ${statusText[status]}`}
          onClick={choose}
        >
          <rect width={W} height={H} fill={RAMP[0]} />
          {LEVELS.map((level, i) => (
            <ellipse
              key={level}
              cx={X(0)}
              cy={Y(0)}
              rx={Math.sqrt((2 * level) / BOWL.a) * PX}
              ry={Math.sqrt((2 * level) / BOWL.b) * PX}
              fill={RAMP[i]}
              stroke="white"
              strokeOpacity="0.7"
            />
          ))}
          <path d={`M${X(0) - 6} ${Y(0)} H${X(0) + 6} M${X(0)} ${Y(0) - 6} V${Y(0) + 6}`} stroke="white" strokeWidth="2.5" />
          <polyline points={visible.map((s) => `${X(s.p.x)},${Y(s.p.y)}`).join(' ')} fill="none" stroke={colour} strokeWidth="2" strokeLinejoin="round" />
          {visible.length < 300 &&
            visible.map((s, i) => <circle key={i} cx={X(s.p.x)} cy={Y(s.p.y)} r="2.5" fill={colour} />)}
          <circle cx={X(start.x)} cy={Y(start.y)} r="6" fill="white" stroke={INK} strokeWidth="2" />
          {Math.abs(current.p.x) < 50 && (
            <circle cx={X(current.p.x)} cy={Y(current.p.y)} r="7" fill={colour} stroke="white" strokeWidth="2.5" />
          )}
          <text x={8} y={16} fontSize="10" fontWeight={600} fill={INK} opacity="0.7">
            steep ↕ · shallow ↔
          </text>
        </svg>
      }
      below={
        <>
          <p className="px-1 text-sm text-slate-700" aria-live="polite">
            {statusText[status]}
          </p>
          <LossChart losses={path.map((s) => bowlLoss(s.p))} colour={colour} />
          {runs.length > 0 && (
            <div className="rounded-2xl bg-white p-3 ring-1 ring-slate-200">
              <p className="text-sm font-semibold text-slate-900">Your runs</p>
              <table className="mt-1 w-full text-left text-sm">
                <thead className="text-xs text-slate-500">
                  <tr>
                    <th className="py-1 font-medium">Optimizer</th>
                    <th className="py-1 font-medium">Learning rate</th>
                    <th className="py-1 font-medium">Result</th>
                  </tr>
                </thead>
                <tbody>
                  {runs.map((run, i) => (
                    <tr key={i} className="border-t border-slate-100">
                      <td className="py-1">
                        <span className="mr-1.5 inline-block size-2 rounded-full" style={{ background: COLOURS[run.optimizer] }} aria-hidden />
                        {NAMES[run.optimizer]}
                      </td>
                      <td className="py-1 font-mono">{run.lr}</td>
                      <td className="py-1">{run.result}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </>
      }
      controls={
        <>
          <Choice
            label="Optimizer"
            value={optimizer}
            onChange={(value) => {
              setOptimizer(value)
              restart()
            }}
            options={[
              { value: 'gd', label: 'GD', swatch: COLOURS.gd },
              { value: 'momentum', label: 'Momentum', swatch: COLOURS.momentum },
              { value: 'adam', label: 'Adam', swatch: COLOURS.adam },
            ]}
          />
          <Slider
            label="Learning rate"
            value={rateIndex}
            min={0}
            max={RATES.length - 1}
            onChange={(value) => {
              setRateIndex(value)
              restart()
            }}
            format={(i) => String(RATES[i])}
          />
          <ButtonRow>
            <Button size="sm" icon={<StepForward className="size-4" />} onClick={() => advance(1)} disabled={done || status === 'running'}>
              Step
            </Button>
            <Button
              size="sm"
              variant="secondary"
              icon={status === 'running' ? <Pause className="size-4" /> : <Play className="size-4" />}
              onClick={() => setStatus(status === 'running' ? 'ready' : 'running')}
              disabled={done}
            >
              {status === 'running' ? 'Pause' : 'Play'}
            </Button>
            <Button size="sm" variant="secondary" icon={<RotateCcw className="size-4" />} onClick={() => restart()}>
              Reset
            </Button>
          </ButtonRow>
          <Readouts
            items={[
              { label: 'Step', value: steps },
              { label: 'Loss', value: Number.isFinite(loss) ? fmt(loss, loss < 1 ? 3 : 1) : '∞' },
            ]}
          />
          <Readouts items={[{ label: 'Steps to minimum', value: status === 'reached' ? steps : '—', note: `loss below ${AT_MINIMUM}` }]} />
          <Hint>Loss = ½(0.2·x² + 8·y²): a valley 40× steeper up-down than left-right.</Hint>
        </>
      }
    />
  )
}

function LossChart({ losses, colour }: { losses: number[]; colour: string }) {
  const w = 400
  const h = 120
  const pad = { left: 36, right: 10, top: 10, bottom: 18 }
  const finite = losses.map((l) => Math.min(Math.max(l, 1e-3), 1e4))
  const n = Math.max(finite.length - 1, 20)
  const x = linear([0, n], [pad.left, w - pad.right])
  const y = linear([-3, 4], [h - pad.bottom, pad.top])
  const every = Math.max(1, Math.floor(finite.length / 300))
  const pts = finite
    .map((l, i) => [i, l] as const)
    .filter(([i]) => i % every === 0 || i === finite.length - 1)
    .map(([i, l]) => `${x(i)},${y(Math.log10(l))}`)
    .join(' ')
  return (
    <figure className="rounded-2xl bg-white p-3 ring-1 ring-slate-200">
      <figcaption className="text-xs font-semibold text-slate-600">Loss per step (log scale)</figcaption>
      <svg viewBox={`0 0 ${w} ${h}`} className="mt-1 block w-full" role="img" aria-label={`Loss after ${losses.length - 1} steps`}>
        {[-2, 0, 2, 4].map((e) => (
          <g key={e}>
            <line x1={pad.left} x2={w - pad.right} y1={y(e)} y2={y(e)} stroke={GRID} />
            <text x={pad.left - 4} y={y(e) + 3} textAnchor="end" fontSize="9" fill={MUTED}>
              {e >= 0 ? 10 ** e : `0.${'0'.repeat(-e - 1)}1`}
            </text>
          </g>
        ))}
        <line x1={pad.left} x2={w - pad.right} y1={y(Math.log10(AT_MINIMUM))} y2={y(Math.log10(AT_MINIMUM))} stroke={INK} strokeOpacity="0.4" strokeDasharray="4 3" />
        <text x={w - pad.right} y={y(Math.log10(AT_MINIMUM)) - 3} textAnchor="end" fontSize="9" fill={MUTED}>
          minimum zone
        </text>
        {finite.length > 1 && <polyline points={pts} fill="none" stroke={colour} strokeWidth="2" strokeLinejoin="round" />}
        <text x={w - pad.right} y={h - 4} textAnchor="end" fontSize="9" fill={MUTED}>
          steps →
        </text>
      </svg>
    </figure>
  )
}
