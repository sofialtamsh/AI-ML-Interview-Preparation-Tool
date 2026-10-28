import { Captions, ChevronLeft, ChevronRight, Pause, Play, RotateCcw, Volume2 } from 'lucide-react'
import { useCallback, useEffect, useRef, useState } from 'react'

import { cn } from '../../lib/cn'
import type { VideoContent } from '../../lib/types'
import { FigureView } from '../Figures'

const canSpeak = () => typeof window !== 'undefined' && 'speechSynthesis' in window

const clock = (ms: number) => {
  const s = Math.max(0, Math.round(ms / 1000))
  return `${Math.floor(s / 60)}:${String(s % 60).padStart(2, '0')}`
}

/** A narrated explainer built from scenes: a figure, a big caption and the narration.
 * Plays recorded narration when it exists; otherwise it can read aloud with the device voice,
 * or simply auto-advance with captions. */
export function VideoPlayer({ video, audioUrl }: { video: VideoContent; audioUrl?: (id: string) => string }) {
  const scenes = video.scenes
  const [index, setIndex] = useState(0)
  const [playing, setPlaying] = useState(false)
  const [finished, setFinished] = useState(false)
  const [elapsed, setElapsed] = useState(0)
  const [captions, setCaptions] = useState(true)
  const [deviceVoice, setDeviceVoice] = useState(false)
  const audioRef = useRef<HTMLAudioElement>(null)

  const scene = scenes[index]
  const audioSrc = scene.audio_id && audioUrl ? audioUrl(scene.audio_id) : null
  const mode: 'audio' | 'voice' | 'timer' = audioSrc ? 'audio' : deviceVoice && canSpeak() ? 'voice' : 'timer'
  const hasRecorded = scenes.some((s) => s.audio_id) && !!audioUrl
  const duration = scene.seconds * 1000
  const total = scenes.reduce((sum, s) => sum + s.seconds * 1000, 0)
  const before = scenes.slice(0, index).reduce((sum, s) => sum + s.seconds * 1000, 0)

  const jump = useCallback((next: number) => {
    setElapsed(0)
    setFinished(false)
    setIndex(next)
  }, [])

  const advance = useCallback(() => {
    if (index < scenes.length - 1) jump(index + 1)
    else {
      setPlaying(false)
      setFinished(true)
      setElapsed(duration)
    }
  }, [duration, index, jump, scenes.length])

  // Recorded narration.
  useEffect(() => {
    const audio = audioRef.current
    if (mode !== 'audio' || !audio) return
    if (playing) audio.play().catch(() => setPlaying(false))
    else audio.pause()
  }, [mode, playing, index])

  // Device voice: reads the scene, then moves on.
  useEffect(() => {
    if (mode !== 'voice' || !playing) return
    const utterance = new SpeechSynthesisUtterance(scene.narration)
    utterance.lang = 'en-IN'
    const voice = window.speechSynthesis.getVoices().find((v) => v.lang === 'en-IN') ?? null
    if (voice) utterance.voice = voice
    utterance.onend = () => advance()
    window.speechSynthesis.cancel()
    window.speechSynthesis.speak(utterance)
    return () => {
      utterance.onend = null
      window.speechSynthesis.cancel()
    }
  }, [mode, playing, scene.narration, advance])

  // Progress clock for the voice and caption modes.
  useEffect(() => {
    if (mode === 'audio' || !playing) return
    const timer = window.setInterval(() => setElapsed((e) => e + 100), 100)
    return () => window.clearInterval(timer)
  }, [mode, playing, index])

  useEffect(() => {
    if (mode === 'timer' && playing && elapsed >= duration) advance()
  }, [mode, playing, elapsed, duration, advance])

  const toggle = () => {
    if (finished) {
      jump(0)
      setPlaying(true)
      return
    }
    setPlaying(!playing)
  }

  return (
    <div className="mx-auto max-w-4xl space-y-3">
      <div className="relative aspect-video overflow-hidden rounded-3xl bg-gradient-to-br from-brand-950 via-brand-900 to-fuchsia-900 text-white shadow-lg">
        <div key={index} className="absolute inset-0 flex animate-fade-up flex-col p-4 sm:p-8">
          <p className="text-xs font-semibold tracking-wide text-white/60 uppercase">
            Scene {index + 1} of {scenes.length} · {scene.title}
          </p>
          <div className="flex min-h-0 flex-1 items-center justify-center py-2">
            {scene.figure ? (
              <div className="h-full max-h-full w-full max-w-md rounded-2xl bg-white/95 p-2 sm:p-4">
                <FigureView name={scene.figure} className="block size-full" />
              </div>
            ) : (
              <span className="text-6xl sm:text-7xl" aria-hidden>
                🎬
              </span>
            )}
          </div>
          <p className="text-center font-display text-lg font-bold text-balance sm:text-3xl">{scene.on_screen}</p>
        </div>
        {!playing && (
          <button
            type="button"
            onClick={toggle}
            aria-label={finished ? 'Replay' : 'Play'}
            className="absolute inset-0 grid place-items-center bg-black/20 transition hover:bg-black/30"
          >
            <span className="grid size-16 place-items-center rounded-full bg-white text-brand-700 shadow-xl">
              {finished ? <RotateCcw className="size-7" /> : <Play className="ml-1 size-7" />}
            </span>
          </button>
        )}
      </div>

      {audioSrc && (
        <audio
          ref={audioRef}
          src={audioSrc}
          preload="auto"
          onTimeUpdate={(event) => setElapsed(event.currentTarget.currentTime * 1000)}
          onEnded={advance}
        />
      )}

      <div className="flex gap-1" aria-hidden>
        {scenes.map((s, i) => (
          <button
            key={i}
            type="button"
            tabIndex={-1}
            onClick={() => jump(i)}
            className="h-1.5 overflow-hidden rounded-full bg-slate-200"
            style={{ flexGrow: s.seconds }}
          >
            <span
              className="block h-full bg-brand-600 transition-[width] duration-100"
              style={{ width: i < index ? '100%' : i === index ? `${Math.min(100, (elapsed / (s.seconds * 1000)) * 100)}%` : '0%' }}
            />
          </button>
        ))}
      </div>

      <div className="flex flex-wrap items-center gap-2">
        <button type="button" onClick={() => jump(Math.max(0, index - 1))} disabled={index === 0} className="grid size-9 place-items-center rounded-full text-slate-700 hover:bg-slate-100 disabled:opacity-40" aria-label="Previous scene">
          <ChevronLeft className="size-5" />
        </button>
        <button type="button" onClick={toggle} className="grid size-10 place-items-center rounded-full bg-brand-600 text-white shadow hover:bg-brand-700" aria-label={playing ? 'Pause' : finished ? 'Replay' : 'Play'}>
          {playing ? <Pause className="size-5" /> : finished ? <RotateCcw className="size-5" /> : <Play className="ml-0.5 size-5" />}
        </button>
        <button type="button" onClick={() => jump(Math.min(scenes.length - 1, index + 1))} disabled={index === scenes.length - 1} className="grid size-9 place-items-center rounded-full text-slate-700 hover:bg-slate-100 disabled:opacity-40" aria-label="Next scene">
          <ChevronRight className="size-5" />
        </button>
        <span className="font-mono text-sm text-slate-600 tabular-nums">
          {clock(before + Math.min(elapsed, duration))} / {clock(total)}
        </span>
        <div className="ml-auto flex gap-1.5">
          {!hasRecorded && canSpeak() && (
            <button
              type="button"
              aria-pressed={deviceVoice}
              onClick={() => {
                setDeviceVoice(!deviceVoice)
                setElapsed(0)
              }}
              className={cn('inline-flex h-8 items-center gap-1.5 rounded-lg px-2.5 text-xs font-semibold ring-1 ring-inset', deviceVoice ? 'bg-slate-900 text-white ring-slate-900' : 'text-slate-700 ring-slate-200 hover:bg-slate-50')}
            >
              <Volume2 className="size-4" aria-hidden /> Read aloud
            </button>
          )}
          <button
            type="button"
            aria-pressed={captions}
            onClick={() => setCaptions(!captions)}
            className={cn('inline-flex h-8 items-center gap-1.5 rounded-lg px-2.5 text-xs font-semibold ring-1 ring-inset', captions ? 'bg-slate-900 text-white ring-slate-900' : 'text-slate-700 ring-slate-200 hover:bg-slate-50')}
          >
            <Captions className="size-4" aria-hidden /> Captions
          </button>
        </div>
      </div>

      {captions && (
        <p className="rounded-2xl bg-white px-4 py-3 text-base leading-relaxed text-slate-800 ring-1 ring-slate-200" aria-live="polite">
          {scene.narration}
        </p>
      )}
    </div>
  )
}
