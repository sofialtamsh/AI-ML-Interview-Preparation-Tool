import { RotateCcw, Sparkles } from 'lucide-react'
import { useEffect, useMemo, useRef, useState, type MouseEvent, type PointerEvent } from 'react'

import { Button } from '../../components/ui/Button'
import { CLASS_A, ERROR_RED, GRID, MUTED, SERIES, clamp, fmt, gaussian, linear, rng, svgPoint, type Point } from '../viz'
import { ButtonRow, Dot, Hint, Legend, Line, Readouts, Slider, Toggle, WidgetFrame } from './controls'
import { leastSquares, mse, rSquared } from './ml'

const W = 400
const H = 300
const PAD = { left: 34, right: 12, top: 12, bottom: 28 }
const X = linear([0, 10], [PAD.left, W - PAD.right])
const Y = linear([0, 10], [H - PAD.bottom, PAD.top])
const TICKS = [0, 2, 4, 6, 8, 10]
const MAX_POINTS = 30

function startingPoints(): Point[] {
  const random = rng(21)
  return Array.from({ length: 12 }, (_, i) => {
    const x = 0.6 + i * 0.78
    return { x, y: clamp(0.7 * x + 1.4 + gaussian(random) * 0.9, 0.2, 9.8) }
  })
}

export function LinearRegression() {
  const [points, setPoints] = useState<Point[]>(startingPoints)
  const [slope, setSlope] = useState(0)
  const [intercept, setIntercept] = useState(5)
  const [showResiduals, setShowResiduals] = useState(true)
  const [showSquares, setShowSquares] = useState(false)
  const [bestShown, setBestShown] = useState(false)
  const svgRef = useRef<SVGSVGElement>(null)
  const drag = useRef<number | null>(null)
  const tween = useRef<number | null>(null)

  useEffect(() => () => {
    if (tween.current) cancelAnimationFrame(tween.current)
  }, [])

  const best = useMemo(() => leastSquares(points), [points])
  const error = mse(points, slope, intercept)
  const bestError = mse(points, best.slope, best.intercept)

  const animateTo = (target: { slope: number; intercept: number }) => {
    if (tween.current) cancelAnimationFrame(tween.current)
    const from = { slope, intercept }
    const started = performance.now()
    const frame = (now: number) => {
      const t = Math.min(1, (now - started) / 600)
      const ease = 1 - (1 - t) ** 3
      setSlope(from.slope + (target.slope - from.slope) * ease)
      setIntercept(from.intercept + (target.intercept - from.intercept) * ease)
      tween.current = t < 1 ? requestAnimationFrame(frame) : null
    }
    tween.current = requestAnimationFrame(frame)
  }

  const toData = (event: { clientX: number; clientY: number }): Point => {
    const p = svgPoint(svgRef.current!, event)
    return { x: clamp(X.invert(p.x), 0, 10), y: clamp(Y.invert(p.y), 0, 10) }
  }

  const addPoint = (event: MouseEvent<SVGSVGElement>) => {
    if (points.length >= MAX_POINTS) return
    const p = toData(event)
    setPoints((current) => [...current, p])
  }

  const onPointMove = (event: PointerEvent<SVGCircleElement>) => {
    if (drag.current === null) return
    const p = toData(event)
    const index = drag.current
    setPoints((current) => current.map((q, i) => (i === index ? p : q)))
  }

  const lineAt = (x: number) => slope * x + intercept
  const residuals = points.map((p) => ({ p, fit: lineAt(p.x) }))

  const plot = (
    <svg
      ref={svgRef}
      viewBox={`0 0 ${W} ${H}`}
      className="block w-full cursor-crosshair select-none"
      role="img"
      aria-label={`Scatter plot with ${points.length} points and the line y = ${fmt(slope)}x + ${fmt(intercept)}`}
      onClick={addPoint}
    >
      <defs>
        <clipPath id="lr-plot">
          <rect x={PAD.left} y={PAD.top} width={W - PAD.left - PAD.right} height={H - PAD.top - PAD.bottom} />
        </clipPath>
      </defs>
      {TICKS.map((t) => (
        <g key={t}>
          <line x1={X(t)} x2={X(t)} y1={PAD.top} y2={H - PAD.bottom} stroke={GRID} />
          <line x1={PAD.left} x2={W - PAD.right} y1={Y(t)} y2={Y(t)} stroke={GRID} />
          <text x={X(t)} y={H - 10} textAnchor="middle" fontSize="10" fill={MUTED}>
            {t}
          </text>
          <text x={PAD.left - 6} y={Y(t) + 3} textAnchor="end" fontSize="10" fill={MUTED}>
            {t}
          </text>
        </g>
      ))}
      <g clipPath="url(#lr-plot)" pointerEvents="none">
        {showSquares &&
          residuals.map(({ p, fit }, i) => {
            const side = Math.abs(Y(p.y) - Y(fit))
            const toLeft = X(p.x) + side > W - PAD.right
            return (
              <rect
                key={`s${i}`}
                x={toLeft ? X(p.x) - side : X(p.x)}
                y={Math.min(Y(p.y), Y(fit))}
                width={side}
                height={side}
                fill={ERROR_RED}
                fillOpacity="0.12"
                stroke={ERROR_RED}
                strokeOpacity="0.45"
              />
            )
          })}
        {showResiduals &&
          residuals.map(({ p, fit }, i) => (
            <line key={`r${i}`} x1={X(p.x)} x2={X(p.x)} y1={Y(p.y)} y2={Y(fit)} stroke={ERROR_RED} strokeWidth="2" />
          ))}
        <line x1={X(0)} y1={Y(lineAt(0))} x2={X(10)} y2={Y(lineAt(10))} stroke={SERIES[5]} strokeWidth="3" strokeLinecap="round" />
      </g>
      {points.map((p, i) => (
        <circle
          key={i}
          cx={X(p.x)}
          cy={Y(p.y)}
          r="6"
          fill={CLASS_A}
          stroke="white"
          strokeWidth="2"
          className="cursor-grab active:cursor-grabbing"
          style={{ touchAction: 'none' }}
          onClick={(event) => event.stopPropagation()}
          onPointerDown={(event) => {
            event.stopPropagation()
            event.currentTarget.setPointerCapture(event.pointerId)
            drag.current = i
          }}
          onPointerMove={onPointMove}
          onPointerUp={() => (drag.current = null)}
          onPointerCancel={() => (drag.current = null)}
        />
      ))}
    </svg>
  )

  return (
    <WidgetFrame
      plot={plot}
      below={
        <>
          <Legend
            items={[
              { label: 'Data point (drag me)', mark: <Dot color={CLASS_A} /> },
              { label: 'Your line', mark: <Line color={SERIES[5]} /> },
              ...(showResiduals ? [{ label: 'Residual (miss)', mark: <Line color={ERROR_RED} /> }] : []),
            ]}
          />
          <p className="px-1 font-mono text-sm text-slate-800">
            ŷ = {fmt(slope)}·x {intercept < 0 ? '−' : '+'} {fmt(Math.abs(intercept))}
          </p>
        </>
      }
      controls={
        <>
          <Slider label="Slope (w)" value={slope} min={-3} max={3} step={0.01} onChange={setSlope} format={(v) => fmt(v)} />
          <Slider label="Intercept (b)" value={intercept} min={-10} max={15} step={0.05} onChange={setIntercept} format={(v) => fmt(v)} />
          <Readouts
            items={[
              { label: 'MSE', value: fmt(error), note: 'lower is better' },
              { label: 'R²', value: fmt(rSquared(points, slope, intercept)), note: '1 = perfect fit' },
            ]}
          />
          {bestShown && (
            <p className="rounded-xl bg-white px-3 py-2 text-xs text-slate-600 ring-1 ring-slate-200">
              Least squares MSE on these points: <strong className="font-mono text-slate-900">{fmt(bestError)}</strong>. No straight line can go lower.
            </p>
          )}
          <ButtonRow>
            <Button
              size="sm"
              icon={<Sparkles className="size-4" />}
              onClick={() => {
                setBestShown(true)
                animateTo(best)
              }}
            >
              Best fit
            </Button>
            <Button
              size="sm"
              variant="secondary"
              icon={<RotateCcw className="size-4" />}
              onClick={() => {
                setPoints(startingPoints())
                setBestShown(false)
              }}
            >
              Reset points
            </Button>
          </ButtonRow>
          <Toggle label="Show residuals" checked={showResiduals} onChange={setShowResiduals} />
          <Toggle label="Show squares" checked={showSquares} onChange={setShowSquares} />
          <Hint>
            Drag points, or tap empty space to add one ({points.length}/{MAX_POINTS}).
          </Hint>
        </>
      }
    />
  )
}
