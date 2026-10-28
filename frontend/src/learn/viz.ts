/** Shared helpers for the playgrounds and figures. Colours follow the validated categorical
 * palette (dataviz skill): slot order is fixed and never cycled. */

export const SERIES = ['#2a78d6', '#eb6834', '#1baf7a', '#eda100', '#e87ba4', '#6250d6'] as const
export const CLASS_A = SERIES[0]
export const CLASS_B = SERIES[1]
export const ERROR_RED = '#e34948'
export const INK = '#0f172a'
export const MUTED = '#64748b'
export const GRID = '#e2e8f0'

export type Point = { x: number; y: number }

/** A deterministic random generator, so "New data" is repeatable in tests. */
export function rng(seed: number) {
  let s = seed >>> 0 || 1
  return () => {
    s ^= s << 13
    s ^= s >>> 17
    s ^= s << 5
    return ((s >>> 0) % 1_000_000) / 1_000_000
  }
}

export function gaussian(random: () => number) {
  const u = Math.max(random(), 1e-9)
  const v = random()
  return Math.sqrt(-2 * Math.log(u)) * Math.cos(2 * Math.PI * v)
}

export const clamp = (value: number, lo: number, hi: number) => Math.min(hi, Math.max(lo, value))

export function linear(domain: [number, number], range: [number, number]) {
  const [d0, d1] = domain
  const [r0, r1] = range
  const scale = (value: number) => r0 + ((value - d0) / (d1 - d0)) * (r1 - r0)
  scale.invert = (pixel: number) => d0 + ((pixel - r0) / (r1 - r0)) * (d1 - d0)
  return scale
}

/** The pointer position inside an SVG, in viewBox units. */
export function svgPoint(svg: SVGSVGElement, event: { clientX: number; clientY: number }): Point {
  const box = svg.getBoundingClientRect()
  const view = svg.viewBox.baseVal
  return {
    x: ((event.clientX - box.left) / box.width) * view.width + view.x,
    y: ((event.clientY - box.top) / box.height) * view.height + view.y,
  }
}

export const fmt = (value: number, digits = 2) =>
  Number.isFinite(value) ? value.toFixed(digits) : '∞'

export function distance(a: Point, b: Point) {
  return Math.hypot(a.x - b.x, a.y - b.y)
}
