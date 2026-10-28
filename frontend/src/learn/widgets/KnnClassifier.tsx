import { Eraser, Shuffle } from 'lucide-react'
import { useMemo, useRef, useState, type KeyboardEvent, type MouseEvent, type PointerEvent } from 'react'

import { Button } from '../../components/ui/Button'
import { CLASS_A, CLASS_B, INK, MUTED, clamp, linear, svgPoint, type Point } from '../viz'
import { ButtonRow, Choice, Dot, Hint, Legend, Readouts, Slider, Toggle, WidgetFrame } from './controls'
import { knnAccuracy, knnVote, makeMoons, type Labelled } from './ml'

// Equal units on both axes, so the neighbour circle stays a circle.
const W = 400
const H = 300
const X = linear([-1.6, 2.6], [0, W])
const Y = linear([-1.3, 1.85], [H, 0])
const PX_PER_UNIT = W / 4.2
const CELL = 10
const COLOURS = [CLASS_A, CLASS_B]
const NAMES = ['Blue', 'Orange']
const MAX_POINTS = 300

const starPath = (cx: number, cy: number, r: number) =>
  Array.from({ length: 10 }, (_, i) => {
    const angle = (Math.PI / 5) * i - Math.PI / 2
    const radius = i % 2 ? r * 0.45 : r
    return `${i ? 'L' : 'M'}${(cx + radius * Math.cos(angle)).toFixed(1)} ${(cy + radius * Math.sin(angle)).toFixed(1)}`
  }).join(' ') + 'Z'

export function KnnClassifier() {
  const [seed, setSeed] = useState(4)
  const [train, setTrain] = useState<Labelled[]>(() => makeMoons(120, 0.3, 4))
  const [test, setTest] = useState<Labelled[]>(() => makeMoons(60, 0.3, 4004))
  const [k, setK] = useState(5)
  const [brush, setBrush] = useState<0 | 1>(1)
  const [showTest, setShowTest] = useState(false)
  const [star, setStar] = useState<Point>({ x: 0.5, y: 0.25 })
  const svgRef = useRef<SVGSVGElement>(null)
  const dragging = useRef(false)

  const region = useMemo(() => {
    const cells: { x: number; y: number; label: 0 | 1; strength: number }[] = []
    if (train.length === 0) return cells
    for (let px = 0; px < W; px += CELL)
      for (let py = 0; py < H; py += CELL) {
        const vote = knnVote(train, { x: X.invert(px + CELL / 2), y: Y.invert(py + CELL / 2) }, k)!
        const share = vote.votes[vote.label] / (vote.votes[0] + vote.votes[1])
        cells.push({ x: px, y: py, label: vote.label, strength: share })
      }
    return cells
  }, [train, k])

  const vote = useMemo(() => knnVote(train, star, k), [train, star, k])
  const trainAccuracy = useMemo(() => knnAccuracy(train, train, k), [train, k])
  const testAccuracy = useMemo(() => (showTest ? knnAccuracy(train, test, k) : null), [train, test, k, showTest])

  const newData = () => {
    const next = seed + 1
    setSeed(next)
    setTrain(makeMoons(120, 0.3, next))
    setTest(makeMoons(60, 0.3, next * 1000 + 4))
  }

  const addPoint = (event: MouseEvent<SVGSVGElement>) => {
    if (!svgRef.current || train.length >= MAX_POINTS) return
    const p = svgPoint(svgRef.current, event)
    setTrain((points) => [...points, { x: X.invert(p.x), y: Y.invert(p.y), label: brush }])
  }

  const moveStar = (event: PointerEvent<SVGGElement>) => {
    if (!dragging.current || !svgRef.current) return
    const p = svgPoint(svgRef.current, event)
    setStar({ x: X.invert(clamp(p.x, 0, W)), y: Y.invert(clamp(p.y, 0, H)) })
  }

  const nudgeStar = (event: KeyboardEvent) => {
    const moves: Record<string, [number, number]> = { ArrowLeft: [-0.05, 0], ArrowRight: [0.05, 0], ArrowUp: [0, 0.05], ArrowDown: [0, -0.05] }
    const move = moves[event.key]
    if (!move) return
    event.preventDefault()
    setStar((s) => ({ x: clamp(s.x + move[0], -1.6, 2.6), y: clamp(s.y + move[1], -1.3, 1.85) }))
  }

  const sx = X(star.x)
  const sy = Y(star.y)

  const plot = (
    <svg
      ref={svgRef}
      viewBox={`0 0 ${W} ${H}`}
      className="block w-full cursor-crosshair select-none"
      role="img"
      aria-label={`k-nearest neighbours map with ${train.length} labelled points and k = ${k}`}
      onClick={addPoint}
    >
      <g shapeRendering="crispEdges">
        {region.map((cell) => (
          <rect
            key={`${cell.x}-${cell.y}`}
            x={cell.x}
            y={cell.y}
            width={CELL}
            height={CELL}
            fill={COLOURS[cell.label]}
            opacity={0.06 + (cell.strength - 0.5) * 0.4}
          />
        ))}
      </g>
      {vote && (
        <g pointerEvents="none">
          <circle cx={sx} cy={sy} r={vote.radius * PX_PER_UNIT} fill="none" stroke={INK} strokeOpacity="0.35" strokeDasharray="4 4" />
          {k <= 25 &&
            vote.neighbours.map((n, i) => (
              <line key={i} x1={sx} y1={sy} x2={X(n.x)} y2={Y(n.y)} stroke={COLOURS[n.label]} strokeWidth="1.5" strokeOpacity="0.8" />
            ))}
        </g>
      )}
      {train.map((p, i) => (
        <circle key={i} cx={X(p.x)} cy={Y(p.y)} r="4.5" fill={COLOURS[p.label]} stroke="white" strokeWidth="1.5" pointerEvents="none" />
      ))}
      {showTest &&
        test.map((p, i) => (
          <circle key={`t${i}`} cx={X(p.x)} cy={Y(p.y)} r="4.5" fill="white" stroke={COLOURS[p.label]} strokeWidth="2.5" pointerEvents="none" />
        ))}
      <g
        role="slider"
        tabIndex={0}
        aria-label="Query star: drag it, or use the arrow keys"
        aria-valuetext={vote ? `Predicted ${NAMES[vote.label]}` : 'No prediction'}
        className="cursor-grab outline-none active:cursor-grabbing"
        style={{ touchAction: 'none' }}
        onClick={(event) => event.stopPropagation()}
        onKeyDown={nudgeStar}
        onPointerDown={(event) => {
          event.stopPropagation()
          event.currentTarget.setPointerCapture(event.pointerId)
          dragging.current = true
        }}
        onPointerMove={moveStar}
        onPointerUp={() => (dragging.current = false)}
        onPointerCancel={() => (dragging.current = false)}
      >
        <circle cx={sx} cy={sy} r="18" fill="transparent" />
        <path d={starPath(sx, sy, 11)} fill={vote ? COLOURS[vote.label] : MUTED} stroke={INK} strokeWidth="2" strokeLinejoin="round" />
      </g>
      {train.length === 0 && (
        <text x={W / 2} y={H / 2} textAnchor="middle" fontSize="14" fontWeight={600} fill={MUTED} pointerEvents="none">
          Tap anywhere to add points
        </text>
      )}
    </svg>
  )

  return (
    <WidgetFrame
      plot={plot}
      below={
        <>
          <Legend
            items={[
              { label: 'Blue class', mark: <Dot color={CLASS_A} /> },
              { label: 'Orange class', mark: <Dot color={CLASS_B} /> },
              ...(showTest ? [{ label: 'Test point (hollow)', mark: <Dot color={MUTED} hollow /> }] : []),
              { label: 'Background = what the model predicts there', mark: <span aria-hidden className="inline-block size-2.5 rounded-sm" style={{ background: `linear-gradient(90deg, ${CLASS_A}55, ${CLASS_B}55)` }} /> },
            ]}
          />
          <p className="px-1 text-sm text-slate-700" aria-live="polite">
            ⭐{' '}
            {vote ? (
              <>
                predicts <strong>{NAMES[vote.label]}</strong>: {vote.votes[0]} blue vs {vote.votes[1]} orange among its{' '}
                {vote.neighbours.length} nearest neighbours
              </>
            ) : (
              'needs some labelled points first'
            )}
          </p>
        </>
      }
      controls={
        <>
          <Choice
            label="Tap the map to add"
            value={brush}
            onChange={setBrush}
            options={[
              { value: 0, label: 'Blue', swatch: CLASS_A },
              { value: 1, label: 'Orange', swatch: CLASS_B },
            ]}
          />
          <Slider label="k (neighbours that vote)" value={k} min={1} max={75} onChange={setK} />
          {k > train.length && train.length > 0 && <Hint>Only {train.length} points, so all of them vote.</Hint>}
          <Toggle label="Show test points" checked={showTest} onChange={setShowTest} disabled={test.length === 0} />
          <Readouts
            items={[
              { label: 'Train accuracy', value: trainAccuracy === null ? '—' : `${Math.round(trainAccuracy * 100)}%` },
              {
                label: 'Test accuracy',
                value: testAccuracy === null ? '—' : `${Math.round(testAccuracy * 100)}%`,
                note: showTest ? (test.length ? undefined : 'no test points') : 'turn on test points',
              },
            ]}
          />
          <ButtonRow>
            <Button size="sm" variant="secondary" icon={<Shuffle className="size-4" />} onClick={newData}>
              New data
            </Button>
            <Button
              size="sm"
              variant="secondary"
              icon={<Eraser className="size-4" />}
              onClick={() => {
                setTrain([])
                setTest([])
                setShowTest(false)
              }}
            >
              Clear
            </Button>
          </ButtonRow>
          <Hint>Drag the ⭐ to ask “what would you predict here?”. Points so far: {train.length}{train.length >= MAX_POINTS ? ' (max)' : ''}.</Hint>
        </>
      }
    />
  )
}
