/** Small animated illustrations for lesson cards and video scenes. Pure SVG + SMIL, so they are
 * crisp at any size, cost nothing to load, and stop animating when the user prefers reduced motion. */

import { useEffect, useState, type ReactNode, type SVGProps } from 'react'

import type { Figure } from '../lib/types'
import { CLASS_A, CLASS_B, ERROR_RED, GRID, INK, MUTED, SERIES } from './viz'

function useReducedMotion() {
  const [reduced, setReduced] = useState(
    () => typeof window !== 'undefined' && !!window.matchMedia?.('(prefers-reduced-motion: reduce)').matches,
  )
  useEffect(() => {
    const query = window.matchMedia?.('(prefers-reduced-motion: reduce)')
    if (!query) return
    const update = () => setReduced(query.matches)
    query.addEventListener?.('change', update)
    return () => query.removeEventListener?.('change', update)
  }, [])
  return reduced
}

type Props = { still: boolean }

/** <animate> that disappears when motion is reduced. */
function Anim({ still, ...props }: Props & SVGProps<SVGAnimateElement>) {
  return still ? null : <animate repeatCount="indefinite" {...props} />
}

const Label = ({ x, y, children }: { x: number; y: number; children: ReactNode }) => (
  <text x={x} y={y} textAnchor="middle" fontSize="9" fontWeight={600} fill={MUTED}>
    {children}
  </text>
)

// Fixed sample points (deterministic, so figures look identical everywhere).
const BLUE_PTS = [[30, 30], [42, 44], [26, 52], [50, 28], [38, 60], [22, 38]]
const ORANGE_PTS = [[70, 72], [84, 60], [76, 88], [92, 80], [64, 92], [88, 96]]

function LabelsVsNoLabels({ still }: Props) {
  const all = [...BLUE_PTS, ...ORANGE_PTS]
  return (
    <>
      <rect x="4" y="12" width="112" height="100" rx="10" fill="#f8fafc" stroke={GRID} />
      {BLUE_PTS.map(([x, y], i) => <circle key={`a${i}`} cx={x} cy={y} r="4.5" fill={CLASS_A} />)}
      {ORANGE_PTS.map(([x, y], i) => <circle key={`b${i}`} cx={x} cy={y} r="4.5" fill={CLASS_B} />)}
      <Label x={60} y={124}>With labels</Label>
      <rect x="124" y="12" width="112" height="100" rx="10" fill="#f8fafc" stroke={GRID} />
      {all.map(([x, y], i) => (
        <circle key={`u${i}`} cx={x + 120} cy={y} r="4.5" fill="#94a3b8">
          <Anim still={still} attributeName="fill" dur="4s" values={`#94a3b8;#94a3b8;${i < 6 ? SERIES[2] : SERIES[5]};${i < 6 ? SERIES[2] : SERIES[5]};#94a3b8`} keyTimes="0;0.3;0.5;0.85;1" />
        </circle>
      ))}
      <Label x={180} y={124}>No labels → find groups</Label>
    </>
  )
}

function TrainTestSplit({ still }: Props) {
  return (
    <>
      {Array.from({ length: 10 }, (_, i) => {
        const test = i >= 8
        const x = 24 + i * 19
        return (
          <rect key={i} x={x} y="44" width="15" height="28" rx="4" fill={test ? CLASS_B : CLASS_A}>
            <Anim still={still} attributeName="x" dur="3.5s" values={`${x};${x};${test ? x + 18 : x - 6};${test ? x + 18 : x - 6};${x}`} keyTimes="0;0.25;0.45;0.85;1" />
          </rect>
        )
      })}
      <Label x={86} y={96}>Train (80%): learn</Label>
      <Label x={204} y={96}>Test (20%): judge</Label>
    </>
  )
}

function DecisionBoundary({ still }: Props) {
  return (
    <>
      <path d="M10 10 H230 V40 C170 40 150 110 90 110 H10 Z" fill={CLASS_A} opacity="0.1" />
      <path d="M230 40 C170 40 150 110 90 110 H230 Z" fill={CLASS_B} opacity="0.1" />
      {BLUE_PTS.map(([x, y], i) => <circle key={`a${i}`} cx={x * 1.4} cy={y * 0.9} r="4.5" fill={CLASS_A} />)}
      {ORANGE_PTS.map(([x, y], i) => <circle key={`b${i}`} cx={x * 1.9} cy={y} r="4.5" fill={CLASS_B} />)}
      <path d="M230 40 C170 40 150 110 90 110" fill="none" stroke={INK} strokeWidth="2" strokeDasharray="260" strokeDashoffset="0">
        <Anim still={still} attributeName="stroke-dashoffset" dur="3s" values="260;0;0" keyTimes="0;0.6;1" />
      </path>
      <Label x={120} y={124}>The model learns a boundary</Label>
    </>
  )
}

function OverfitUnderfit() {
  const pts = [[12, 70], [24, 58], [36, 62], [48, 42], [60, 46], [72, 30]]
  const panel = (dx: number, path: string, title: string, tone: string) => (
    <g transform={`translate(${dx},0)`}>
      <rect x="2" y="12" width="76" height="80" rx="8" fill="#f8fafc" stroke={GRID} />
      {pts.map(([x, y], i) => <circle key={i} cx={x} cy={y + 8} r="3" fill={CLASS_A} />)}
      <path d={path} fill="none" stroke={tone} strokeWidth="2" />
      <Label x={40} y={106}>{title}</Label>
    </g>
  )
  return (
    <>
      {panel(0, 'M6 58 H76', 'Underfit', ERROR_RED)}
      {panel(80, 'M6 82 C30 74 50 52 76 34', 'Just right', SERIES[2])}
      {panel(160, 'M6 84 L12 78 L24 60 L36 76 L48 44 L60 60 L72 32 L76 30', 'Overfit', ERROR_RED)}
    </>
  )
}

function Clusters({ still }: Props) {
  const groups = [
    { c: [50, 40], pts: [[40, 30], [58, 34], [46, 50], [62, 48], [36, 44]] },
    { c: [180, 40], pts: [[170, 30], [190, 32], [176, 52], [194, 48], [184, 24]] },
    { c: [115, 92], pts: [[104, 84], [122, 82], [110, 102], [128, 98], [116, 108]] },
  ]
  const starts = [[110, 60], [130, 50], [120, 70]]
  return (
    <>
      {groups.map((g, gi) =>
        g.pts.map(([x, y], i) => (
          <circle key={`${gi}-${i}`} cx={x} cy={y} r="4" fill="#94a3b8">
            <Anim still={still} attributeName="fill" dur="4s" values={`#94a3b8;#94a3b8;${SERIES[gi]};${SERIES[gi]};#94a3b8`} keyTimes="0;0.35;0.55;0.9;1" />
          </circle>
        )),
      )}
      {groups.map((g, gi) => (
        <g key={`c${gi}`}>
          <path d="M-6 0 H6 M0 -6 V6" stroke={INK} strokeWidth="3" strokeLinecap="round" transform={`translate(${g.c[0]},${g.c[1]})`}>
            {!still && (
              <animateTransform attributeName="transform" type="translate" dur="4s" repeatCount="indefinite"
                values={`${starts[gi][0]},${starts[gi][1]};${starts[gi][0]},${starts[gi][1]};${g.c[0]},${g.c[1]};${g.c[0]},${g.c[1]};${starts[gi][0]},${starts[gi][1]}`}
                keyTimes="0;0.2;0.55;0.9;1" />
            )}
          </path>
        </g>
      ))}
      <Label x={120} y={124}>Centroids slide to the middle of each group</Label>
    </>
  )
}

const SCATTER = [[20, 96], [40, 84], [60, 80], [80, 66], [100, 64], [120, 50], [140, 52], [160, 38], [180, 34], [200, 22]]

function ScatterLine({ still }: Props) {
  return (
    <>
      <line x1="10" y1="112" x2="230" y2="112" stroke={GRID} />
      <line x1="10" y1="8" x2="10" y2="112" stroke={GRID} />
      {SCATTER.map(([x, y], i) => <circle key={i} cx={x} cy={y} r="4" fill={CLASS_A} />)}
      <line x1="12" y1="100" x2="220" y2="18" stroke={SERIES[5]} strokeWidth="2.5" strokeLinecap="round">
        <Anim still={still} attributeName="y1" dur="4s" values="60;60;100;100;60" keyTimes="0;0.2;0.55;0.9;1" />
        <Anim still={still} attributeName="y2" dur="4s" values="60;60;18;18;60" keyTimes="0;0.2;0.55;0.9;1" />
      </line>
      <Label x={120} y={124}>Fit the line that misses least</Label>
    </>
  )
}

function Residuals({ still }: Props) {
  const line = (x: number) => 100 - (x - 12) * (82 / 208)
  return (
    <>
      <line x1="12" y1="100" x2="220" y2="18" stroke={SERIES[5]} strokeWidth="2.5" />
      {SCATTER.map(([x, y], i) => {
        const yl = line(x)
        const wobble = i % 2 ? 10 : -9
        const py = y + wobble
        return (
          <g key={i}>
            <line x1={x} y1={yl} x2={x} y2={py} stroke={ERROR_RED} strokeWidth="2">
              <Anim still={still} attributeName="y2" dur="3s" values={`${yl};${py};${py}`} keyTimes="0;0.4;1" />
            </line>
            <circle cx={x} cy={py} r="4" fill={CLASS_A} />
          </g>
        )
      })}
      <Label x={120} y={124}>Residual = real − predicted</Label>
    </>
  )
}

function Neuron({ still }: Props) {
  const inputs = [24, 60, 96]
  return (
    <>
      {inputs.map((y, i) => (
        <g key={i}>
          <line x1="34" y1={y} x2="120" y2="60" stroke={i === 1 ? CLASS_B : CLASS_A} strokeWidth={[3, 1.5, 2.5][i]} />
          <circle cx="24" cy={y} r="11" fill="white" stroke={INK} strokeWidth="1.5" />
          <text x="24" y={y + 3.5} textAnchor="middle" fontSize="10" fill={INK}>x{i + 1}</text>
          {!still && (
            <circle r="3" fill={SERIES[3]}>
              <animateMotion dur="2s" repeatCount="indefinite" path={`M34 ${y} L120 60`} begin={`${i * 0.2}s`} />
            </circle>
          )}
        </g>
      ))}
      <circle cx="132" cy="60" r="20" fill="white" stroke={SERIES[5]} strokeWidth="2.5" />
      <text x="132" y="56" textAnchor="middle" fontSize="11" fill={INK}>Σ + b</text>
      <text x="132" y="70" textAnchor="middle" fontSize="10" fill={MUTED}>σ(·)</text>
      <line x1="152" y1="60" x2="206" y2="60" stroke={INK} strokeWidth="2" markerEnd="url(#arrow)" />
      <text x="220" y="64" textAnchor="middle" fontSize="11" fontWeight={700} fill={INK}>a</text>
      <Label x={120} y={124}>weighted sum + bias → activation</Label>
    </>
  )
}

function Network({ still }: Props) {
  const layers = [[30, 60, 90], [20, 47, 74, 101], [45, 75]]
  const xs = [40, 120, 200]
  const edges: [number, number, number, number][] = []
  for (let l = 0; l < 2; l++)
    for (const y1 of layers[l]) for (const y2 of layers[l + 1]) edges.push([xs[l], y1, xs[l + 1], y2])
  return (
    <>
      {edges.map(([x1, y1, x2, y2], i) => (
        <line key={i} x1={x1} y1={y1} x2={x2} y2={y2} stroke={i % 3 ? CLASS_A : CLASS_B} strokeOpacity="0.45" strokeWidth={1 + (i % 3)} />
      ))}
      {!still &&
        edges.filter((_, i) => i % 4 === 0).map(([x1, y1, x2, y2], i) => (
          <circle key={`p${i}`} r="2.5" fill={SERIES[3]}>
            <animateMotion dur="1.6s" repeatCount="indefinite" begin={`${(i % 5) * 0.25 + (x1 > 100 ? 0.8 : 0)}s`} path={`M${x1} ${y1} L${x2} ${y2}`} />
          </circle>
        ))}
      {layers.map((ys, l) =>
        ys.map((y) => <circle key={`${l}-${y}`} cx={xs[l]} cy={y} r="9" fill="white" stroke={l === 1 ? SERIES[5] : INK} strokeWidth="2" />),
      )}
      <Label x={40} y={122}>Input</Label>
      <Label x={120} y={122}>Hidden</Label>
      <Label x={200} y={122}>Output</Label>
    </>
  )
}

function ActivationCurves({ still }: Props) {
  const sig = Array.from({ length: 41 }, (_, i) => {
    const z = -6 + i * 0.3
    return `${10 + i * 5.5},${100 - (1 / (1 + Math.exp(-z))) * 80}`
  }).join(' ')
  return (
    <>
      <line x1="10" y1="100" x2="230" y2="100" stroke={GRID} />
      <line x1="120" y1="10" x2="120" y2="112" stroke={GRID} />
      <polyline points={sig} fill="none" stroke={CLASS_A} strokeWidth="2.5" strokeDasharray="320">
        <Anim still={still} attributeName="stroke-dashoffset" dur="3s" values="320;0;0" keyTimes="0;0.5;1" />
      </polyline>
      <polyline points="10,100 120,100 230,20" fill="none" stroke={CLASS_B} strokeWidth="2.5" strokeDasharray="260">
        <Anim still={still} attributeName="stroke-dashoffset" dur="3s" values="260;260;0" keyTimes="0;0.3;0.8" />
      </polyline>
      <text x="40" y="32" fontSize="10" fontWeight={700} fill={CLASS_A}>sigmoid</text>
      <text x="178" y="58" fontSize="10" fontWeight={700} fill={CLASS_B}>ReLU</text>
    </>
  )
}

const bowl = (x: number) => 20 + ((x - 120) / 100) ** 2 * 80

function LossBowl({ still }: Props) {
  const curve = Array.from({ length: 41 }, (_, i) => `${20 + i * 5},${bowl(20 + i * 5)}`).join(' ')
  const steps = [30, 62, 86, 102, 112, 117, 120]
  return (
    <>
      <polyline points={curve} fill="none" stroke={INK} strokeWidth="2" />
      {steps.map((x, i) => <circle key={i} cx={x} cy={bowl(x) - 6} r="2" fill={MUTED} opacity="0.5" />)}
      <circle r="7" fill={SERIES[3]} stroke="white" strokeWidth="2" cx={steps[0]} cy={bowl(steps[0]) - 7}>
        <Anim still={still} attributeName="cx" dur="4s" values={steps.join(';') + `;${steps[0]}`} />
        <Anim still={still} attributeName="cy" dur="4s" values={steps.map((x) => bowl(x) - 7).join(';') + `;${bowl(steps[0]) - 7}`} />
      </circle>
      <Label x={120} y={124}>Step downhill until the loss stops dropping</Label>
    </>
  )
}

function LearningRate() {
  const mini = (dx: number, xs: number[], title: string, tone: string) => {
    const f = (x: number) => 18 + ((x - 40) / 32) ** 2 * 60
    return (
      <g transform={`translate(${dx},0)`}>
        <polyline points={Array.from({ length: 17 }, (_, i) => `${8 + i * 4},${f(8 + i * 4)}`).join(' ')} fill="none" stroke={GRID} strokeWidth="2" />
        <polyline points={xs.map((x) => `${x},${f(x) - 3}`).join(' ')} fill="none" stroke={tone} strokeWidth="1.5" />
        {xs.map((x, i) => <circle key={i} cx={x} cy={f(x) - 3} r="2.5" fill={tone} />)}
        <Label x={40} y={106}>{title}</Label>
      </g>
    )
  }
  return (
    <>
      {mini(0, [10, 13, 16, 19, 22, 25], 'Too small: slow', SERIES[3])}
      {mini(80, [10, 30, 37, 40], 'Just right', SERIES[2])}
      {mini(160, [30, 52, 26, 58, 18, 66], 'Too big: bounces', ERROR_RED)}
    </>
  )
}

const FIGURES: Record<Figure, (props: Props) => ReactNode> = {
  labels_vs_no_labels: LabelsVsNoLabels,
  train_test_split: TrainTestSplit,
  decision_boundary: DecisionBoundary,
  overfit_underfit: OverfitUnderfit,
  clusters: Clusters,
  scatter_line: ScatterLine,
  residuals: Residuals,
  neuron: Neuron,
  network: Network,
  activation_curves: ActivationCurves,
  loss_bowl: LossBowl,
  learning_rate: LearningRate,
}

export function FigureView({ name, className }: { name: Figure; className?: string }) {
  const still = useReducedMotion()
  const Draw = FIGURES[name]
  return (
    <svg viewBox="0 0 240 130" className={className} role="img" aria-label={name.replace(/_/g, ' ')}>
      <defs>
        <marker id="arrow" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse">
          <path d="M0 0 L10 5 L0 10 z" fill={INK} />
        </marker>
      </defs>
      <Draw still={still} />
    </svg>
  )
}
