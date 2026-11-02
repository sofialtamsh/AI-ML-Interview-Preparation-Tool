import { useEffect } from 'react'

import { api } from '../lib/api'
import type { ContentComponent } from '../lib/types'

const TICK_SECONDS = 5
/** Without input for this long, the student is probably away (unless a video or audio is playing). */
const IDLE_SECONDS = 120
/** Send once about a minute of active time has built up. */
const SEND_AT_SECONDS = 60
const MAX_REPORT_SECONDS = 120 // the server's limit per report

const INPUT_EVENTS = ['pointerdown', 'pointermove', 'keydown', 'wheel', 'scroll', 'touchstart'] as const

function mediaPlaying(): boolean {
  return Array.from(document.querySelectorAll<HTMLMediaElement>('audio, video')).some((media) => !media.paused && !media.ended)
}

/**
 * Counts time the student actively spends on a topic section: the tab is visible and they've
 * interacted recently, or a video or audio is playing. Reported about once a minute and when they
 * leave; the server also caps it at wall-clock time, so a second tab can't double it.
 */
export function useLearningTime(topic: string, component: ContentComponent | null) {
  useEffect(() => {
    if (!topic || !component) return
    let pending = 0
    let lastInput = Date.now()
    const onInput = () => {
      lastInput = Date.now()
    }

    const send = (leaving = false) => {
      const seconds = Math.min(Math.round(pending), MAX_REPORT_SECONDS)
      pending = 0
      if (seconds < 1) return
      api('/student/progress/time', { method: 'POST', body: { topic, component, seconds }, keepalive: leaving }).catch(() => {
        // Learning time is best effort; a lost report is never worth bothering the student.
      })
    }

    const timer = window.setInterval(() => {
      const visible = document.visibilityState === 'visible'
      const recent = Date.now() - lastInput < IDLE_SECONDS * 1000
      if (visible && (recent || mediaPlaying())) pending += TICK_SECONDS
      if (pending >= SEND_AT_SECONDS) send()
    }, TICK_SECONDS * 1000)

    const onHidden = () => {
      if (document.visibilityState === 'hidden') send(true)
    }
    const onPageHide = () => send(true)

    for (const name of INPUT_EVENTS) window.addEventListener(name, onInput, { capture: true, passive: true })
    document.addEventListener('visibilitychange', onHidden)
    window.addEventListener('pagehide', onPageHide)
    return () => {
      window.clearInterval(timer)
      for (const name of INPUT_EVENTS) window.removeEventListener(name, onInput, { capture: true })
      document.removeEventListener('visibilitychange', onHidden)
      window.removeEventListener('pagehide', onPageHide)
      send(true)
    }
  }, [topic, component])
}
