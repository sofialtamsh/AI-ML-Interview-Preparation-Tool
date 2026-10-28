import { Pause, Play, RotateCcw } from 'lucide-react'
import { useCallback, useEffect, useMemo, useRef, useState } from 'react'

import { Button } from '../../components/ui/Button'
import { CLASS_A, CLASS_B, GRID, INK, MUTED, SERIES, fmt, linear } from '../viz'
import { ButtonRow, Choice, Dot, Hint, Legend, Line, Readouts, Slider, WidgetFrame } from './controls'
import { initNet, makePattern, netAccuracy, predict, trainStep, type ActivationName, type Net, type Pattern } from './ml'

const SIZE = 300
const S = linear([-1.25, 1.25], [0, SIZE])
const SY = linear([-1.25, 1.25], [SIZE, 0])
const MAP_RES = 60
const RATES = [0.01, 0.03, 0.1, 0.3, 1, 3, 10, 20]
const MAX_EPOCHS = 5000
const POSITIVE = SERIES[5]
const NEGATIVE = SERIES[3]

const hexToRgb = (hex: string) => [1, 3, 5].map((i) => parseInt(hex.slice(i, i + 2), 16))
const RGB_A = hexToRgb(CLASS_A)
const RGB_B = hexToRgb(CLASS_B)

export function NeuralNetwork() {
  const [pattern, setPattern] = useState<Pattern>('xor')
  const [hidden, setHidden] = useState(3)
  const [activation, setActivation] = useState<ActivationName>('tanh')
  const [rateIndex, setRateIndex] = useState(4)
  const [running, setRunning] = useState(false)
  const [seed, setSeed] = useState(7)
  const [, setTick] = useState(0)
  const net = useRef<Net>(initNet(3, 7))
  const losses = useRef<number[]>([])
  const canvasRef = useRef<HTMLCanvasElement>(null)

  const data = useMemo(() => makePattern(pattern, 1), [pattern])
  const lr = RATES[rateIndex]

  const reset = useCallback((nextHidden: number, nextSeed: number) => {
    net.current = initNet(nextHidden, nextSeed)
    losses.current = []
    setRunning(false)
    setTick((t) => t + 1)
  }, [])

  useEffect(() => {
    if (!running) return
    let frame = 0
    const loop = () => {
      for (let i = 0; i < 3; i++) losses.current.push(trainStep(net.current, activation, data, lr))
      setTick((t) => t + 1)
      if (losses.current.length >= MAX_EPOCHS) setRunning(false)
      else frame = requestAnimationFrame(loop)
    }
    frame = requestAnimationFrame(loop)
    return () => cancelAnimationFrame(frame)
  }, [running, activation, data, lr])

  // The decision map is painted pixel by pixel on a small canvas and scaled up smoothly.
  useEffect(() => {
    const canvas = canvasRef.current
    const ctx = canvas?.getContext('2d')
    if (!canvas || !ctx) return
    const image = ctx.createImageData(MAP_RES, MAP_RES)
    for (let row = 0; row < MAP_RES; row++)
      for (let col = 0; col < MAP_RES; col++) {
        const x = -1.25 + ((col + 0.5) / MAP_RES) * 2.5
        const y = 1.25 - ((row + 0.5) / MAP_RES) * 2.5
        const p = predict(net.current, activation, { x, y })
        const rgb = p >= 0.5 ? RGB_B : RGB_A
        const alpha = 0.08 + Math.abs(p - 0.5) * 0.7
        const at = (row * MAP_RES + col) * 4
        for (let c = 0; c < 3; c++) image.data[at + c] = Math.round(255 - (255 - rgb[c]) * alpha)
        image.data[at + 3] = 255
      }
    ctx.putImageData(image, 0, 0)
  })

  const history = losses.current
  const loss = history.length ? history[history.length - 1] : null
  const accuracy = netAccuracy(net.current, activation, data)

  const changeAndReset = (apply: () => void, nextHidden = hidden) => {
    apply()
    reset(nextHidden, seed)
  }

  return (
    <WidgetFrame
      plot={
        <div className="grid gap-3 p-3 sm:grid-cols-[minmax(0,1fr)_minmax(0,1fr)]">
          <div className="relative aspect-square w-full overflow-hidden rounded-xl ring-1 ring-slate-200">
            <canvas ref={canvasRef} width={MAP_RES} height={MAP_RES} className="absolute inset-0 size-full" aria-hidden />
            <svg viewBox={`0 0 ${SIZE} ${SIZE}`} className="absolute inset-0 size-full" role="img" aria-label={`Decision map for the ${pattern} pattern, accuracy ${Math.round(accuracy * 100)}%`}>
              {data.map((p, i) => (
                <circle key={i} cx={S(p.x)} cy={SY(p.y)} r="4" fill={p.label ? CLASS_B : CLASS_A} stroke="white" strokeWidth="1.5" />
              ))}
            </svg>
          </div>
          <div className="space-y-3">
            <NetworkDiagram net={net.current} />
            <LossChart losses={history} />
          </div>
        </div>
      }
      below={
        <Legend
          items={[
            { label: 'Class 0', mark: <Dot color={CLASS_A} /> },
            { label: 'Class 1', mark: <Dot color={CLASS_B} /> },
            { label: 'Positive weight', mark: <Line color={POSITIVE} /> },
            { label: 'Negative weight', mark: <Line color={NEGATIVE} /> },
          ]}
        />
      }
      controls={
        <>
          <Choice
            label="Pattern to learn"
            value={pattern}
            onChange={(value) => changeAndReset(() => setPattern(value))}
            options={[
              { value: 'xor', label: 'XOR' },
              { value: 'circle', label: 'Circle' },
              { value: 'blobs', label: 'Two blobs' },
            ]}
          />
          <Slider
            label="Hidden neurons"
            value={hidden}
            min={1}
            max={6}
            onChange={(value) => changeAndReset(() => setHidden(value), value)}
          />
          <Choice
            label="Activation"
            value={activation}
            onChange={(value) => changeAndReset(() => setActivation(value))}
            options={[
              { value: 'tanh', label: 'tanh' },
              { value: 'relu', label: 'ReLU' },
              { value: 'sigmoid', label: 'Sigmoid' },
              { value: 'linear', label: 'Linear' },
            ]}
          />
          <Slider label="Learning rate" value={rateIndex} min={0} max={RATES.length - 1} onChange={setRateIndex} format={(i) => String(RATES[i])} />
          <ButtonRow>
            <Button
              size="sm"
              icon={running ? <Pause className="size-4" /> : <Play className="size-4" />}
              onClick={() => setRunning((r) => !r)}
              disabled={history.length >= MAX_EPOCHS}
            >
              {running ? 'Pause' : 'Train'}
            </Button>
            <Button
              size="sm"
              variant="secondary"
              icon={<RotateCcw className="size-4" />}
              onClick={() => {
                setSeed(seed + 1)
                reset(hidden, seed + 1)
              }}
            >
              Reset
            </Button>
          </ButtonRow>
          <Readouts
            items={[
              { label: 'Epoch', value: history.length },
              { label: 'Loss', value: loss === null ? '—' : fmt(loss, 3) },
              { label: 'Accuracy', value: `${Math.round(accuracy * 100)}%` },
            ]}
          />
          <Hint>Reset draws new random starting weights.</Hint>
        </>
      }
    />
  )
}

function NetworkDiagram({ net }: { net: Net }) {
  const w = 260
  const h = 150
  const hidden = net.w1.length
  const inputY = [h * 0.33, h * 0.67]
  const hiddenY = Array.from({ length: hidden }, (_, j) => (h * (j + 1)) / (hidden + 1))
  const xs = [30, w / 2, w - 30]
  const stroke = (weight: number) => ({
    stroke: weight >= 0 ? POSITIVE : NEGATIVE,
    strokeWidth: Math.min(7, 0.6 + Math.abs(weight) * 1.2),
    strokeOpacity: 0.85,
  })
  return (
    <svg viewBox={`0 0 ${w} ${h}`} className="block w-full rounded-xl bg-slate-50 ring-1 ring-slate-200" role="img" aria-label={`Network with 2 inputs, ${hidden} hidden neurons and 1 output`}>
      {hiddenY.map((hy, j) => (
        <g key={j}>
          {inputY.map((iy, i) => (
            <line key={i} x1={xs[0]} y1={iy} x2={xs[1]} y2={hy} {...stroke(net.w1[j][i])} />
          ))}
          <line x1={xs[1]} y1={hy} x2={xs[2]} y2={h / 2} {...stroke(net.w2[j])} />
        </g>
      ))}
      {inputY.map((iy, i) => (
        <g key={`in${i}`}>
          <circle cx={xs[0]} cy={iy} r="11" fill="white" stroke={INK} strokeWidth="1.5" />
          <text x={xs[0]} y={iy + 4} textAnchor="middle" fontSize="10" fill={INK}>
            x{i + 1}
          </text>
        </g>
      ))}
      {hiddenY.map((hy, j) => (
        <circle key={`h${j}`} cx={xs[1]} cy={hy} r="9" fill="white" stroke={INK} strokeWidth="1.5" />
      ))}
      <circle cx={xs[2]} cy={h / 2} r="11" fill="white" stroke={INK} strokeWidth="1.5" />
      <text x={xs[2]} y={h / 2 + 4} textAnchor="middle" fontSize="10" fill={INK}>
        ŷ
      </text>
    </svg>
  )
}

function LossChart({ losses }: { losses: number[] }) {
  const w = 260
  const h = 120
  const pad = { left: 30, bottom: 18, top: 8, right: 8 }
  const n = Math.max(losses.length, 100)
  const max = Math.max(1, ...losses)
  const x = linear([0, n], [pad.left, w - pad.right])
  const y = linear([0, max], [h - pad.bottom, pad.top])
  const every = Math.max(1, Math.floor(losses.length / 260))
  const points = losses
    .filter((_, i) => i % every === 0 || i === losses.length - 1)
    .map((l, i, all) => `${x(i === all.length - 1 ? losses.length - 1 : i * every)},${y(l)}`)
    .join(' ')
  return (
    <figure>
      <figcaption className="text-xs font-semibold text-slate-600">Training loss</figcaption>
      <svg viewBox={`0 0 ${w} ${h}`} className="mt-1 block w-full" role="img" aria-label={losses.length ? `Loss now ${fmt(losses[losses.length - 1], 3)}` : 'No training yet'}>
        {[0, max / 2, max].map((v) => (
          <g key={v}>
            <line x1={pad.left} x2={w - pad.right} y1={y(v)} y2={y(v)} stroke={GRID} />
            <text x={pad.left - 4} y={y(v) + 3} textAnchor="end" fontSize="9" fill={MUTED}>
              {fmt(v, 1)}
            </text>
          </g>
        ))}
        <text x={w - pad.right} y={h - 4} textAnchor="end" fontSize="9" fill={MUTED}>
          epochs →
        </text>
        {losses.length > 1 && <polyline points={points} fill="none" stroke={SERIES[0]} strokeWidth="2" strokeLinejoin="round" />}
        {losses.length === 0 && (
          <text x={w / 2} y={h / 2} textAnchor="middle" fontSize="11" fill={MUTED}>
            Press Train
          </text>
        )}
      </svg>
    </figure>
  )
}
