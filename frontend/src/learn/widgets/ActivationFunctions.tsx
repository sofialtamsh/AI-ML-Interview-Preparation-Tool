import { useMemo, useState } from 'react'

import { GRID, INK, MUTED, SERIES, fmt, linear } from '../viz'
import { Choice, Hint, Legend, Line, Readouts, Slider, WidgetFrame } from './controls'
import { ACTIVATIONS, LEAKY_SLOPE, steepestSlope, type ActivationName } from './ml'

const W = 400
const H = 260
const PAD = { left: 34, right: 12, top: 14, bottom: 24 }
const X = linear([-6, 6], [PAD.left, W - PAD.right])
const WIDE = { range: [-1, 6] as [number, number], ticks: [0, 2, 4, 6] }
const AXES: Record<string, { range: [number, number]; ticks: number[] }> = {
  sigmoid: { range: [-0.2, 1.2], ticks: [0, 0.5, 1] },
  tanh: { range: [-1.2, 1.2], ticks: [-1, 0, 1] },
  relu: WIDE,
  leaky_relu: WIDE,
  gelu: WIDE,
}
const OUTPUT = SERIES[0]
const SLOPE = SERIES[1]
const CHOICES: ActivationName[] = ['sigmoid', 'tanh', 'relu', 'leaky_relu', 'gelu']

/** 9.5 × 10⁻⁷ style formatting for tiny gradients. */
function scientific(value: number) {
  if (value >= 0.001) return fmt(value, value >= 10 ? 1 : 3)
  const exponent = Math.floor(Math.log10(value))
  const superscript = String(exponent).replace(/[-0-9]/g, (c) => '⁻⁰¹²³⁴⁵⁶⁷⁸⁹'['-0123456789'.indexOf(c)])
  return `${fmt(value / 10 ** exponent, 1)} × 10${superscript}`
}

export function ActivationFunctions() {
  const [name, setName] = useState<ActivationName>('sigmoid')
  const [z, setZ] = useState(0)
  const [layers, setLayers] = useState(5)
  const { f, df } = ACTIVATIONS[name]
  const { range, ticks } = AXES[name]
  const Y = linear(range, [H - PAD.bottom, PAD.top])
  const steepest = useMemo(() => steepestSlope(name), [name])

  const curve = (fn: (v: number) => number) =>
    Array.from({ length: 241 }, (_, i) => {
      const v = -6 + i * 0.05
      return `${X(v).toFixed(1)},${Y(fn(v)).toFixed(1)}`
    }).join(' ')

  const out = f(z)
  const slope = df(z)
  const tangent = [z - 0.9, z + 0.9].map((v) => ({ x: X(v), y: Y(out + slope * (v - z)) }))

  const gradients = Array.from({ length: layers }, (_, i) => steepest ** (i + 1))
  const barMax = Math.max(1, ...gradients)

  return (
    <WidgetFrame
      plot={
        <svg viewBox={`0 0 ${W} ${H}`} className="block w-full" role="img" aria-label={`${ACTIVATIONS[name].label}: at z = ${fmt(z)} output ${fmt(out, 3)}, slope ${fmt(slope, 3)}`}>
          <defs>
            <clipPath id="act-plot">
              <rect x={PAD.left} y={PAD.top} width={W - PAD.left - PAD.right} height={H - PAD.top - PAD.bottom} />
            </clipPath>
          </defs>
          {[-6, -4, -2, 0, 2, 4, 6].map((t) => (
            <g key={t}>
              <line x1={X(t)} x2={X(t)} y1={PAD.top} y2={H - PAD.bottom} stroke={GRID} strokeWidth={t === 0 ? 1.5 : 1} />
              <text x={X(t)} y={H - 8} textAnchor="middle" fontSize="10" fill={MUTED}>
                {t}
              </text>
            </g>
          ))}
          {ticks.map((t) => (
            <g key={t}>
              <line x1={PAD.left} x2={W - PAD.right} y1={Y(t)} y2={Y(t)} stroke={GRID} strokeWidth={t === 0 ? 1.5 : 1} />
              <text x={PAD.left - 5} y={Y(t) + 3} textAnchor="end" fontSize="10" fill={MUTED}>
                {fmt(t, Number.isInteger(t) ? 0 : 1)}
              </text>
            </g>
          ))}
          <g clipPath="url(#act-plot)">
            <polyline points={curve(df)} fill="none" stroke={SLOPE} strokeWidth="2" strokeDasharray="6 4" />
            <polyline points={curve(f)} fill="none" stroke={OUTPUT} strokeWidth="2.5" />
            <line x1={tangent[0].x} y1={tangent[0].y} x2={tangent[1].x} y2={tangent[1].y} stroke={INK} strokeWidth="1.5" />
            <line x1={X(z)} x2={X(z)} y1={PAD.top} y2={H - PAD.bottom} stroke={INK} strokeOpacity="0.25" strokeDasharray="3 3" />
            <circle cx={X(z)} cy={Y(slope)} r="5" fill={SLOPE} stroke="white" strokeWidth="2" />
            <circle cx={X(z)} cy={Y(out)} r="6" fill={OUTPUT} stroke="white" strokeWidth="2" />
          </g>
        </svg>
      }
      below={
        <>
          <Legend
            items={[
              { label: 'Output f(z) for input z (across)', mark: <Line color={OUTPUT} /> },
              { label: 'Slope f′(z) (the gradient it passes back)', mark: <Line color={SLOPE} dashed /> },
            ]}
          />
          <div className="rounded-2xl bg-white p-3 ring-1 ring-slate-200">
            <p className="text-sm font-semibold text-slate-900">Gradient after {layers} layers, best case</p>
            <p className="text-xs text-slate-500">
              Each layer multiplies the gradient by its slope. Even at its steepest, {ACTIVATIONS[name].label} gives ×{fmt(steepest, 2)} per layer.
            </p>
            <div className="mt-3 flex h-24 items-end gap-1" role="img" aria-label={`Gradient shrinks to ${scientific(gradients[gradients.length - 1])} after ${layers} layers`}>
              {gradients.map((g, i) => (
                <div key={i} className="flex h-full flex-1 flex-col justify-end" title={`Layer ${i + 1} back: ${scientific(g)}`}>
                  <div className="rounded-t-[4px] transition-all duration-300" style={{ height: `${Math.max(1.5, (g / barMax) * 100)}%`, background: SERIES[5] }} />
                </div>
              ))}
            </div>
            <div className="mt-1 flex justify-between text-[11px] text-slate-500">
              <span>1 layer back</span>
              <span>{layers} layers back</span>
            </div>
            <p className="mt-2 text-sm text-slate-700">
              Reaching the first layer: <strong className="font-mono">{fmt(steepest, 2)}<sup>{layers}</sup> ≈ {scientific(gradients[gradients.length - 1])}</strong>
              {steepest > 1.01 && ' (above 1 multiplies up: gradients can explode instead)'}
            </p>
          </div>
        </>
      }
      controls={
        <>
          <Choice
            label="Function"
            value={name}
            onChange={setName}
            options={CHOICES.map((value) => ({ value, label: ACTIVATIONS[value].label }))}
          />
          <Slider label="Input z" value={z} min={-6} max={6} step={0.1} onChange={setZ} format={(v) => fmt(v, 1)} />
          <Readouts
            items={[
              { label: 'Output', value: fmt(out, 3) },
              { label: 'Slope', value: fmt(slope, 3) },
            ]}
          />
          <Slider label="Layers stacked" value={layers} min={1} max={20} onChange={setLayers} />
          {name === 'leaky_relu' && <Hint>Leaky slope for negatives here: {LEAKY_SLOPE} (libraries often default to 0.01).</Hint>}
          {name === 'gelu' && <Hint>GELU uses the common tanh approximation.</Hint>}
        </>
      }
    />
  )
}
