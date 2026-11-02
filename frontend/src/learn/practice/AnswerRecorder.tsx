import { Download, Mic, RotateCcw, Square, Video, X } from 'lucide-react'
import { useEffect, useRef, useState, type ReactNode } from 'react'

import { Button } from '../../components/ui/Button'
import { Alert, Spinner } from '../../components/ui/Feedback'
import { cn } from '../../lib/cn'
import { formatClock } from './FeedbackView'
import { useAnswerRecorder, type Recording } from './useAnswerRecorder'

// Most interview answers should land between one and two minutes.
const SWEET_SPOT = [60, 120] as const

function LiveView({ stream, level, caption, children }: { stream: MediaStream | null; level: number; caption?: string; children?: ReactNode }) {
  const videoRef = useRef<HTMLVideoElement>(null)
  const hasVideo = !!stream && stream.getVideoTracks().length > 0
  useEffect(() => {
    if (videoRef.current) videoRef.current.srcObject = stream
  }, [stream])
  return (
    <div className="relative aspect-video overflow-hidden rounded-3xl bg-slate-900">
      {hasVideo ? (
        <video ref={videoRef} autoPlay muted playsInline className="size-full -scale-x-100 object-cover" aria-label="Your camera" />
      ) : (
        <div className="flex size-full items-center justify-center bg-gradient-to-br from-brand-700 via-violet-700 to-fuchsia-700">
          <span className="relative flex size-24 items-center justify-center rounded-full bg-white/15" style={{ transform: `scale(${1 + level * 0.5})` }}>
            <Mic className="size-10 text-white" aria-hidden />
          </span>
        </div>
      )}
      <div className="absolute top-3 right-3 flex h-6 items-end gap-0.5" aria-hidden>
        {[0.15, 0.35, 0.55, 0.75, 0.95].map((threshold) => (
          <span key={threshold} className={cn('w-1.5 rounded-full transition-all', level >= threshold ? 'bg-emerald-400' : 'bg-white/30')} style={{ height: `${8 + threshold * 16}px` }} />
        ))}
      </div>
      {caption && (
        // The question stays in sight while answering, like a teleprompter.
        <p className="absolute inset-x-0 bottom-0 bg-gradient-to-t from-slate-950/85 to-transparent px-4 pt-8 pb-3 text-sm font-semibold text-white sm:text-base">
          {caption}
        </p>
      )}
      {children}
    </div>
  )
}

function TimeBar({ elapsed, max }: { elapsed: number; max: number }) {
  const [from, to] = SWEET_SPOT
  return (
    <div>
      <div className="relative h-2.5 overflow-hidden rounded-full bg-slate-200">
        <div className="absolute inset-y-0 bg-emerald-200" style={{ left: `${(from / max) * 100}%`, width: `${((to - from) / max) * 100}%` }} />
        <div className={cn('absolute inset-y-0 left-0 rounded-full transition-[width]', elapsed > to ? 'bg-amber-500' : 'bg-brand-600')} style={{ width: `${(elapsed / max) * 100}%` }} />
      </div>
      <div className="mt-1.5 flex justify-between text-xs text-slate-500">
        <span className="font-semibold text-slate-900 tabular-nums">{formatClock(elapsed)}</span>
        <span>
          <span className="inline-block size-2 rounded-full bg-emerald-300 align-middle" aria-hidden /> sweet spot {formatClock(from)}–{formatClock(to)}
        </span>
        <span className="tabular-nums">max {formatClock(max)}</span>
      </div>
    </div>
  )
}

/**
 * Records a spoken answer to one question. The recording stays in this browser: the parent
 * decides what happens next (e.g. sends the voice for feedback) through `actions`.
 */
export function AnswerRecorder({
  question,
  maxSeconds,
  actions,
  onReset,
  onRecorded,
  onCannotRecord,
  onClose,
}: {
  question: string
  maxSeconds: number
  actions: (recording: Recording) => ReactNode
  onReset?: () => void
  /** A take finished (whether or not feedback is asked for). */
  onRecorded?: () => void
  /** The camera or mic couldn't be used (blocked, missing, unsupported). */
  onCannotRecord?: () => void
  onClose: () => void
}) {
  const recorder = useAnswerRecorder(maxSeconds)
  const [camera, setCamera] = useState(true)
  const { phase, recording } = recorder
  const stageRef = useRef<HTMLDivElement>(null)

  // Bring the camera (and later the playback) fully into view, clear of the sticky tab bar.
  useEffect(() => {
    if (phase === 'ready' || phase === 'recorded') stageRef.current?.scrollIntoView?.({ behavior: 'smooth', block: 'center' })
    if (phase === 'recorded') onRecorded?.()
  }, [phase])

  useEffect(() => {
    if (recorder.error) onCannotRecord?.()
  }, [recorder.error])

  const retake = () => {
    onReset?.()
    void recorder.open(camera)
  }
  const close = () => {
    recorder.reset()
    onReset?.()
    onClose()
  }

  return (
    <div className="space-y-4">
      <div className="flex items-start justify-between gap-3">
        <p className="font-display text-lg font-bold text-slate-900">{question}</p>
        <Button variant="ghost" size="sm" onClick={close} aria-label="Close recorder">
          <X className="size-4" />
        </Button>
      </div>

      {recorder.error && <Alert>{recorder.error}</Alert>}

      {phase === 'idle' && (
        <div className="space-y-3 rounded-3xl bg-slate-50 p-5 ring-1 ring-slate-200">
          <div className="flex flex-wrap gap-2" role="radiogroup" aria-label="Recording mode">
            {[
              { value: true, label: 'Camera + mic', icon: Video },
              { value: false, label: 'Voice only', icon: Mic },
            ].map((option) => (
              <button
                key={option.label}
                type="button"
                role="radio"
                aria-checked={camera === option.value}
                onClick={() => setCamera(option.value)}
                className={cn(
                  'inline-flex items-center gap-1.5 rounded-xl px-3.5 py-2 text-sm font-semibold ring-1 transition',
                  camera === option.value ? 'bg-slate-900 text-white ring-slate-900' : 'bg-white text-slate-700 ring-slate-200 hover:bg-slate-100',
                )}
              >
                <option.icon className="size-4" aria-hidden /> {option.label}
              </button>
            ))}
          </div>
          <p className="text-sm text-slate-600">
            🔒 Your video stays on this device.
          </p>
          <Button variant="glow" size="lg" onClick={() => void recorder.open(camera)}>
            {camera ? 'Turn on camera' : 'Turn on mic'}
          </Button>
        </div>
      )}

      {phase === 'starting' && (
        <div className="flex aspect-video items-center justify-center gap-2 rounded-3xl bg-slate-100 text-sm text-slate-600">
          <Spinner className="size-4" /> Asking for your {camera ? 'camera and mic' : 'mic'}…
        </div>
      )}

      {(phase === 'ready' || phase === 'countdown' || phase === 'recording') && (
        <div ref={stageRef} className="mx-auto w-full max-w-3xl space-y-3">
          <LiveView stream={recorder.stream} level={recorder.level} caption={phase === 'ready' ? undefined : question}>
            {phase === 'countdown' && (
              <div className="absolute inset-0 flex items-center justify-center bg-slate-900/40" aria-live="assertive">
                <span key={recorder.countdown} className="animate-fade-up font-display text-8xl font-bold text-white drop-shadow-lg">
                  {recorder.countdown}
                </span>
              </div>
            )}
            {phase === 'recording' && (
              <span className="absolute top-3 left-3 inline-flex items-center gap-1.5 rounded-full bg-rose-600 px-2.5 py-1 text-xs font-bold text-white">
                <span className="size-2 animate-pulse rounded-full bg-white" aria-hidden /> REC {formatClock(recorder.elapsed)}
              </span>
            )}
          </LiveView>
          {phase === 'recording' && <TimeBar elapsed={recorder.elapsed} max={maxSeconds} />}
          <div className="flex flex-wrap items-center gap-2">
            {phase === 'ready' && (
              <>
                <Button variant="glow" size="lg" onClick={recorder.begin} icon={<span className="size-3 rounded-full bg-rose-400" aria-hidden />}>
                  Start answering
                </Button>
                <span className="text-sm text-slate-500">3-2-1, then talk. Aim for 1–2 minutes.</span>
              </>
            )}
            {phase === 'recording' && (
              <Button variant="danger" size="lg" onClick={() => void recorder.finish()} icon={<Square className="size-4 fill-current" />}>
                I&apos;m done
              </Button>
            )}
          </div>
        </div>
      )}

      {phase === 'finishing' && (
        <div className="flex aspect-video items-center justify-center gap-2 rounded-3xl bg-slate-100 text-sm text-slate-600">
          <Spinner className="size-4" /> Wrapping up your recording…
        </div>
      )}

      {phase === 'recorded' && recording && (
        <div ref={stageRef} className="mx-auto w-full max-w-3xl space-y-3">
          {recording.kind === 'video' ? (
            <video src={recording.url} controls playsInline className="aspect-video w-full rounded-3xl bg-slate-900" aria-label="Your recorded answer" />
          ) : (
            <audio src={recording.url} controls className="w-full" aria-label="Your recorded answer" />
          )}
          <div className="flex flex-wrap items-center gap-2">
            {actions(recording)}
            <Button variant="secondary" onClick={retake} icon={<RotateCcw className="size-4" />}>
              Retake
            </Button>
            <a
              href={recording.url}
              download={`my-answer.${recording.mimeType.includes('mp4') ? 'mp4' : 'webm'}`}
              className="inline-flex h-10 items-center gap-2 rounded-xl px-4 text-sm font-semibold text-slate-700 hover:bg-slate-100"
            >
              <Download className="size-4" aria-hidden /> Save to device
            </a>
            <span className="text-sm text-slate-500 tabular-nums">{formatClock(recording.durationMs / 1000)} recorded</span>
          </div>
        </div>
      )}
    </div>
  )
}
