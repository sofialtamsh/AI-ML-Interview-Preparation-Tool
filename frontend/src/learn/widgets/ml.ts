/** The maths behind the playgrounds. Pure functions, so they are unit-tested apart from the UI. */

import { gaussian, rng, type Point } from '../viz'

export type Labelled = Point & { label: 0 | 1 }

const sq = (a: Point, b: Point) => (a.x - b.x) ** 2 + (a.y - b.y) ** 2

// --- k-nearest neighbours -------------------------------------------------------------------

/** sklearn's make_moons: two interleaving half circles. */
export function makeMoons(n: number, noise: number, seed: number): Labelled[] {
  const random = rng(seed)
  return Array.from({ length: n }, (_, i) => {
    const label = (i % 2) as 0 | 1
    const t = random() * Math.PI
    const x = label === 0 ? Math.cos(t) : 1 - Math.cos(t)
    const y = label === 0 ? Math.sin(t) : 0.5 - Math.sin(t)
    return { x: x + gaussian(random) * noise, y: y + gaussian(random) * noise, label }
  })
}

export type Vote = { label: 0 | 1; votes: [number, number]; neighbours: Labelled[]; radius: number }

/** Majority vote among the k nearest points; a tie goes to the single nearest point. */
export function knnVote(train: Labelled[], query: Point, k: number): Vote | null {
  if (train.length === 0) return null
  const ranked = train.map((p) => ({ p, d: sq(p, query) })).sort((a, b) => a.d - b.d)
  const neighbours = ranked.slice(0, Math.min(k, ranked.length))
  const ones = neighbours.filter((n) => n.p.label === 1).length
  const zeros = neighbours.length - ones
  const label = ones === zeros ? neighbours[0].p.label : ones > zeros ? 1 : 0
  return {
    label,
    votes: [zeros, ones],
    neighbours: neighbours.map((n) => n.p),
    radius: Math.sqrt(neighbours[neighbours.length - 1].d),
  }
}

/** Share of points the model labels correctly. Training points count themselves as a neighbour,
 * exactly like scoring a fitted sklearn model on its own training data. */
export function knnAccuracy(train: Labelled[], points: Labelled[], k: number): number | null {
  if (train.length === 0 || points.length === 0) return null
  const correct = points.filter((p) => knnVote(train, p, k)?.label === p.label).length
  return correct / points.length
}

// --- k-means ---------------------------------------------------------------------------------

/** Gaussian blobs with well separated centres inside [0, 10] × [0, 7.5]. */
export function makeBlobs(blobs: number, perBlob: number, seed: number): Point[] {
  const random = rng(seed)
  const centres: Point[] = []
  for (let attempt = 0; centres.length < blobs && attempt < 500; attempt++) {
    const c = { x: 1.6 + random() * 6.8, y: 1.4 + random() * 4.7 }
    if (centres.every((other) => sq(other, c) > 2.6 ** 2)) centres.push(c)
  }
  return centres.flatMap((c) =>
    Array.from({ length: perBlob }, () => ({
      x: c.x + gaussian(random) * 0.55,
      y: c.y + gaussian(random) * 0.55,
    })),
  )
}

export function nearest(point: Point, centroids: Point[]): number {
  let best = 0
  for (let i = 1; i < centroids.length; i++) if (sq(point, centroids[i]) < sq(point, centroids[best])) best = i
  return best
}

export const assignClusters = (points: Point[], centroids: Point[]) => points.map((p) => nearest(p, centroids))

/** Move each centroid to the mean of its points; an empty cluster keeps its place. */
export function updateCentroids(points: Point[], labels: number[], centroids: Point[]): Point[] {
  return centroids.map((c, i) => {
    const members = points.filter((_, j) => labels[j] === i)
    if (members.length === 0) return c
    return {
      x: members.reduce((s, p) => s + p.x, 0) / members.length,
      y: members.reduce((s, p) => s + p.y, 0) / members.length,
    }
  })
}

export function inertia(points: Point[], labels: number[], centroids: Point[]): number {
  return points.reduce((s, p, i) => s + sq(p, centroids[labels[i]]), 0)
}

/** k distinct data points as starting centroids (Forgy initialisation). */
export function randomStarts(points: Point[], k: number, random: () => number): Point[] {
  const pool = [...points]
  const starts: Point[] = []
  while (starts.length < k && pool.length) starts.push(pool.splice(Math.floor(random() * pool.length), 1)[0])
  return starts.map((p) => ({ ...p }))
}

/** Lowest inertia over several runs, like sklearn's n_init: used for the elbow chart. */
export function bestInertia(points: Point[], k: number, seed: number, runs = 6): number {
  const random = rng(seed)
  let best = Infinity
  for (let run = 0; run < runs; run++) {
    let centroids = randomStarts(points, k, random)
    let labels = assignClusters(points, centroids)
    for (let step = 0; step < 100; step++) {
      centroids = updateCentroids(points, labels, centroids)
      const next = assignClusters(points, centroids)
      const changed = next.some((label, i) => label !== labels[i])
      labels = next
      if (!changed) break
    }
    best = Math.min(best, inertia(points, labels, centroids))
  }
  return best
}

// --- linear regression -----------------------------------------------------------------------

export function leastSquares(points: Point[]): { slope: number; intercept: number } {
  const n = points.length
  const mx = points.reduce((s, p) => s + p.x, 0) / n
  const my = points.reduce((s, p) => s + p.y, 0) / n
  const sxx = points.reduce((s, p) => s + (p.x - mx) ** 2, 0)
  const sxy = points.reduce((s, p) => s + (p.x - mx) * (p.y - my), 0)
  const slope = sxx === 0 ? 0 : sxy / sxx
  return { slope, intercept: my - slope * mx }
}

export function mse(points: Point[], slope: number, intercept: number): number {
  return points.reduce((s, p) => s + (p.y - (slope * p.x + intercept)) ** 2, 0) / points.length
}

export function rSquared(points: Point[], slope: number, intercept: number): number {
  const my = points.reduce((s, p) => s + p.y, 0) / points.length
  const total = points.reduce((s, p) => s + (p.y - my) ** 2, 0)
  return total === 0 ? 0 : 1 - (mse(points, slope, intercept) * points.length) / total
}

// --- activation functions --------------------------------------------------------------------

export type ActivationName = 'sigmoid' | 'tanh' | 'relu' | 'leaky_relu' | 'gelu' | 'linear'

const sigmoid = (z: number) => 1 / (1 + Math.exp(-z))
const GELU_C = Math.sqrt(2 / Math.PI)
const gelu = (z: number) => 0.5 * z * (1 + Math.tanh(GELU_C * (z + 0.044715 * z ** 3)))
export const LEAKY_SLOPE = 0.1

export const ACTIVATIONS: Record<ActivationName, { label: string; f: (z: number) => number; df: (z: number) => number }> = {
  sigmoid: { label: 'Sigmoid', f: sigmoid, df: (z) => sigmoid(z) * (1 - sigmoid(z)) },
  tanh: { label: 'tanh', f: Math.tanh, df: (z) => 1 - Math.tanh(z) ** 2 },
  relu: { label: 'ReLU', f: (z) => Math.max(0, z), df: (z) => (z > 0 ? 1 : 0) },
  leaky_relu: { label: 'Leaky ReLU', f: (z) => (z > 0 ? z : LEAKY_SLOPE * z), df: (z) => (z > 0 ? 1 : LEAKY_SLOPE) },
  gelu: { label: 'GELU', f: gelu, df: (z) => (gelu(z + 1e-4) - gelu(z - 1e-4)) / 2e-4 },
  linear: { label: 'Linear', f: (z) => z, df: () => 1 },
}

/** The steepest slope a function ever has: the best case for a gradient passing through it. */
export function steepestSlope(name: ActivationName): number {
  let best = 0
  for (let z = -6; z <= 6; z += 0.01) best = Math.max(best, ACTIVATIONS[name].df(z))
  return best
}

// --- a tiny neural network (2 inputs → hidden layer → 1 sigmoid output) ----------------------

export type Pattern = 'xor' | 'circle' | 'blobs'

export function makePattern(pattern: Pattern, seed: number): Labelled[] {
  const random = rng(seed)
  const noise = () => gaussian(random)
  if (pattern === 'xor') {
    return Array.from({ length: 120 }, (_, i) => {
      const sx = i % 2 ? 1 : -1
      const sy = i % 4 < 2 ? 1 : -1
      return { x: sx * 0.5 + noise() * 0.17, y: sy * 0.5 + noise() * 0.17, label: (sx * sy < 0 ? 1 : 0) as 0 | 1 }
    })
  }
  if (pattern === 'circle') {
    return Array.from({ length: 140 }, (_, i) => {
      const inside = i % 2 === 0
      const r = inside ? Math.sqrt(random()) * 0.38 : 0.62 + random() * 0.3
      const t = random() * 2 * Math.PI
      return { x: r * Math.cos(t), y: r * Math.sin(t), label: (inside ? 1 : 0) as 0 | 1 }
    })
  }
  return Array.from({ length: 120 }, (_, i) => {
    const label = (i % 2) as 0 | 1
    const c = label ? { x: 0.42, y: 0.38 } : { x: -0.42, y: -0.36 }
    return { x: c.x + noise() * 0.22, y: c.y + noise() * 0.22, label }
  })
}

export type Net = { w1: [number, number][]; b1: number[]; w2: number[]; b2: number }

export function initNet(hidden: number, seed: number): Net {
  const random = rng(seed)
  return {
    w1: Array.from({ length: hidden }, () => [gaussian(random) * 1.2, gaussian(random) * 1.2]),
    b1: Array.from({ length: hidden }, () => gaussian(random) * 0.3),
    w2: Array.from({ length: hidden }, () => gaussian(random) / Math.sqrt(hidden)),
    b2: 0,
  }
}

export function predict(net: Net, activation: ActivationName, p: Point): number {
  const act = ACTIVATIONS[activation].f
  let z = net.b2
  for (let j = 0; j < net.w1.length; j++) z += net.w2[j] * act(net.w1[j][0] * p.x + net.w1[j][1] * p.y + net.b1[j])
  return sigmoid(z)
}

/** One full-batch gradient-descent step on binary cross-entropy. Returns the loss before the step. */
export function trainStep(net: Net, activation: ActivationName, data: Labelled[], lr: number): number {
  const { f, df } = ACTIVATIONS[activation]
  const h = net.w1.length
  const gw1 = net.w1.map(() => [0, 0])
  const gb1 = new Array(h).fill(0)
  const gw2 = new Array(h).fill(0)
  let gb2 = 0
  let loss = 0
  for (const p of data) {
    const pre = net.w1.map((w, j) => w[0] * p.x + w[1] * p.y + net.b1[j])
    const hid = pre.map(f)
    const out = sigmoid(hid.reduce((s, a, j) => s + a * net.w2[j], net.b2))
    const clipped = Math.min(Math.max(out, 1e-7), 1 - 1e-7)
    loss -= p.label ? Math.log(clipped) : Math.log(1 - clipped)
    const dz = out - p.label
    gb2 += dz
    for (let j = 0; j < h; j++) {
      gw2[j] += dz * hid[j]
      const dpre = dz * net.w2[j] * df(pre[j])
      gw1[j][0] += dpre * p.x
      gw1[j][1] += dpre * p.y
      gb1[j] += dpre
    }
  }
  const n = data.length
  for (let j = 0; j < h; j++) {
    net.w1[j][0] -= (lr * gw1[j][0]) / n
    net.w1[j][1] -= (lr * gw1[j][1]) / n
    net.b1[j] -= (lr * gb1[j]) / n
    net.w2[j] -= (lr * gw2[j]) / n
  }
  net.b2 -= (lr * gb2) / n
  return loss / n
}

export function netAccuracy(net: Net, activation: ActivationName, data: Labelled[]): number {
  return data.filter((p) => (predict(net, activation, p) >= 0.5 ? 1 : 0) === p.label).length / data.length
}

// --- gradient descent on a stretched bowl ----------------------------------------------------

/** loss(x, y) = ½(A·x² + B·y²): shallow along x, steep along y (condition number 40). */
export const BOWL = { a: 0.2, b: 8 }
export const bowlLoss = (p: Point) => 0.5 * (BOWL.a * p.x ** 2 + BOWL.b * p.y ** 2)
export const AT_MINIMUM = 0.01

export type Optimizer = 'gd' | 'momentum' | 'adam'
export type OptState = { p: Point; v: Point; m: Point; s: Point; t: number }

export const startState = (p: Point): OptState => ({ p, v: { x: 0, y: 0 }, m: { x: 0, y: 0 }, s: { x: 0, y: 0 }, t: 0 })

export function optimizerStep(state: OptState, optimizer: Optimizer, lr: number): OptState {
  const g = { x: BOWL.a * state.p.x, y: BOWL.b * state.p.y }
  const t = state.t + 1
  if (optimizer === 'gd') return { ...state, t, p: { x: state.p.x - lr * g.x, y: state.p.y - lr * g.y } }
  if (optimizer === 'momentum') {
    const v = { x: 0.9 * state.v.x + g.x, y: 0.9 * state.v.y + g.y }
    return { ...state, t, v, p: { x: state.p.x - lr * v.x, y: state.p.y - lr * v.y } }
  }
  const m = { x: 0.9 * state.m.x + 0.1 * g.x, y: 0.9 * state.m.y + 0.1 * g.y }
  const s = { x: 0.999 * state.s.x + 0.001 * g.x ** 2, y: 0.999 * state.s.y + 0.001 * g.y ** 2 }
  const mh = 1 - 0.9 ** t
  const sh = 1 - 0.999 ** t
  const step = (mi: number, si: number) => (lr * (mi / mh)) / (Math.sqrt(si / sh) + 1e-8)
  return { ...state, t, m, s, p: { x: state.p.x - step(m.x, s.x), y: state.p.y - step(m.y, s.y) } }
}
