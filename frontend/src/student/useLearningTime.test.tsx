import { render } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi, type Mock } from 'vitest'

import type { ContentComponent } from '../lib/types'
import { useLearningTime } from './useLearningTime'

function Probe({ component }: { component: ContentComponent | null }) {
  useLearningTime('machine-learning/regression', component)
  return null
}

let fetch: Mock<(url: string, init: RequestInit) => Promise<Response>>

function sent() {
  return fetch.mock.calls.map(([url, init]) => ({
    url,
    ...JSON.parse(String(init.body)),
    keepalive: init.keepalive,
  }))
}

function setVisibility(state: 'visible' | 'hidden') {
  Object.defineProperty(document, 'visibilityState', { value: state, configurable: true })
  document.dispatchEvent(new Event('visibilitychange'))
}

beforeEach(() => {
  vi.useFakeTimers()
  fetch = vi.fn(async () => new Response(null, { status: 204 }))
  vi.stubGlobal('fetch', fetch)
  setVisibility('visible')
})

afterEach(() => {
  vi.useRealTimers()
  vi.unstubAllGlobals()
  document.body.innerHTML = ''
})

describe('learning time', () => {
  it('reports a minute of active time, then the rest when the student leaves', () => {
    const view = render(<Probe component="lesson" />)
    for (let i = 0; i < 18; i++) {
      window.dispatchEvent(new Event('pointerdown'))
      vi.advanceTimersByTime(5_000)
    }
    expect(sent()).toEqual([{ url: '/api/student/progress/time', topic: 'machine-learning/regression', component: 'lesson', seconds: 60, keepalive: false }])

    view.unmount()
    expect(sent()[1]).toMatchObject({ component: 'lesson', seconds: 30, keepalive: true })
  })

  it('stops counting after two idle minutes', () => {
    const view = render(<Probe component="quiz" />)
    vi.advanceTimersByTime(10 * 60_000)
    view.unmount()
    // 23 ticks of 5 s before the idle limit: 60 sent on the way, 55 when leaving.
    expect(sent().map((r) => r.seconds)).toEqual([60, 55])
  })

  it('keeps counting while a video or audio plays without input', () => {
    const audio = document.createElement('audio')
    Object.defineProperty(audio, 'paused', { value: false })
    document.body.append(audio)
    const view = render(<Probe component="video" />)
    vi.advanceTimersByTime(5 * 60_000)
    view.unmount()
    expect(sent().reduce((sum, r) => sum + r.seconds, 0)).toBe(300)
  })

  it('sends what it has when the tab is hidden, and pauses while hidden', () => {
    render(<Probe component="lesson" />)
    vi.advanceTimersByTime(20_000)
    setVisibility('hidden')
    expect(sent()).toEqual([expect.objectContaining({ seconds: 20, keepalive: true })])
    window.dispatchEvent(new Event('keydown'))
    vi.advanceTimersByTime(5 * 60_000)
    expect(sent()).toHaveLength(1)
  })

  it('does nothing until the topic has loaded', () => {
    const view = render(<Probe component={null} />)
    vi.advanceTimersByTime(5 * 60_000)
    view.unmount()
    expect(fetch).not.toHaveBeenCalled()
  })
})
