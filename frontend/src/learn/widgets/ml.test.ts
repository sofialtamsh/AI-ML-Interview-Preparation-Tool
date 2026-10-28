import { describe, expect, it } from 'vitest'

import { rng } from '../viz'
import {
  ACTIVATIONS,
  AT_MINIMUM,
  assignClusters,
  bestInertia,
  bowlLoss,
  initNet,
  knnAccuracy,
  knnVote,
  leastSquares,
  makeBlobs,
  makeMoons,
  makePattern,
  mse,
  netAccuracy,
  optimizerStep,
  rSquared,
  randomStarts,
  startState,
  steepestSlope,
  trainStep,
  updateCentroids,
  type ActivationName,
  type Optimizer,
} from './ml'

describe('k-nearest neighbours', () => {
  const train = makeMoons(120, 0.3, 4)
  const test = makeMoons(60, 0.3, 99)

  it('memorises the training set at k = 1 and generalises better with a larger k', () => {
    expect(knnAccuracy(train, train, 1)).toBe(1)
    expect(knnAccuracy(train, test, 15)!).toBeGreaterThan(knnAccuracy(train, test, 1)!)
  })

  it('breaks ties with the nearest point and caps k at the data size', () => {
    const pts = [
      { x: 0, y: 0, label: 1 as const },
      { x: 1, y: 0, label: 0 as const },
    ]
    const vote = knnVote(pts, { x: 0.1, y: 0 }, 50)!
    expect(vote.neighbours).toHaveLength(2)
    expect(vote.label).toBe(1)
    expect(knnVote([], { x: 0, y: 0 }, 3)).toBeNull()
  })
})

describe('k-means', () => {
  const points = makeBlobs(3, 40, 5)

  it('never increases inertia and finds the elbow at the true blob count', () => {
    const random = rng(3)
    let centroids = randomStarts(points, 3, random)
    let labels = assignClusters(points, centroids)
    let last = Infinity
    for (let i = 0; i < 10; i++) {
      centroids = updateCentroids(points, labels, centroids)
      labels = assignClusters(points, centroids)
      const now = points.reduce((s, p, j) => s + (p.x - centroids[labels[j]].x) ** 2 + (p.y - centroids[labels[j]].y) ** 2, 0)
      expect(now).toBeLessThanOrEqual(last + 1e-9)
      last = now
    }
    const curve = [1, 2, 3, 4, 5].map((k) => bestInertia(points, k, 1))
    const drops = curve.slice(1).map((v, i) => curve[i] - v)
    expect(drops[1]).toBeGreaterThan(drops[2] * 3) // big drop to k = 3, small after
  })
})

describe('linear regression', () => {
  it('least squares beats any other line', () => {
    const pts = [1, 2, 3, 4, 5, 6].map((x, i) => ({ x, y: 2 * x + 1 + (i % 2 ? 0.4 : -0.4) }))
    const fit = leastSquares(pts)
    expect(fit.slope).toBeCloseTo(2 + 1.2 / 17.5, 6)
    const best = mse(pts, fit.slope, fit.intercept)
    expect(mse(pts, fit.slope + 0.05, fit.intercept)).toBeGreaterThan(best)
    expect(mse(pts, fit.slope, fit.intercept - 0.1)).toBeGreaterThan(best)
    expect(rSquared(pts, fit.slope, fit.intercept)).toBeGreaterThan(0.95)
  })
})

describe('activation functions', () => {
  it('has the textbook values and slopes', () => {
    expect(ACTIVATIONS.sigmoid.df(0)).toBeCloseTo(0.25)
    expect(steepestSlope('sigmoid')).toBeCloseTo(0.25, 3)
    expect(steepestSlope('relu')).toBe(1)
    expect(ACTIVATIONS.gelu.f(1)).toBeCloseTo(0.841, 3)
    expect(ACTIVATIONS.leaky_relu.df(-2)).toBeGreaterThan(0)
    expect(ACTIVATIONS.relu.df(-2)).toBe(0)
  })
})

describe('tiny neural network', () => {
  const xor = makePattern('xor', 1)
  const train = (hidden: number, activation: ActivationName, lr: number, epochs: number) => {
    const net = initNet(hidden, 7)
    const losses = Array.from({ length: epochs }, () => trainStep(net, activation, xor, lr))
    return { net, losses }
  }

  it('needs several non-linear hidden neurons to solve XOR', () => {
    const one = train(1, 'tanh', 1, 600)
    const four = train(4, 'tanh', 1, 600)
    const linear = train(4, 'linear', 1, 600)
    expect(one.losses.at(-1)!).toBeGreaterThan(0.4)
    expect(netAccuracy(four.net, 'tanh', xor)).toBe(1)
    expect(linear.losses.at(-1)!).toBeCloseTo(Math.log(2), 2)
  })

  it('jumps around with a learning rate that is too high', () => {
    const { losses } = train(4, 'tanh', 10, 400)
    expect(Math.max(...losses)).toBeGreaterThan(2)
  })
})

describe('optimizers on the stretched bowl', () => {
  const stepsToMinimum = (optimizer: Optimizer, lr: number) => {
    let state = startState({ x: -4.2, y: 2.5 })
    for (let i = 1; i <= 3000; i++) {
      state = optimizerStep(state, optimizer, lr)
      const loss = bowlLoss(state.p)
      if (!Number.isFinite(loss) || loss > 1e6) return -1
      if (loss < AT_MINIMUM) return i
    }
    return Infinity
  }

  it('crawls with a tiny rate, diverges with a huge one, and momentum and Adam beat zig-zagging GD', () => {
    expect(stepsToMinimum('gd', 0.01)).toBeGreaterThan(1000)
    expect(stepsToMinimum('gd', 0.3)).toBe(-1)
    const zigzag = stepsToMinimum('gd', 0.15)
    expect(stepsToMinimum('momentum', 0.15)).toBeLessThan(zigzag)
    expect(stepsToMinimum('adam', 0.15)).toBeLessThan(zigzag)
  })
})
