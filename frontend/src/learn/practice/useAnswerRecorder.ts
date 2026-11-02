import { useCallback, useEffect, useRef, useState } from 'react'

import { toSpeechWav } from './wav'

export type RecorderPhase = 'idle' | 'starting' | 'ready' | 'countdown' | 'recording' | 'finishing' | 'recorded'

export type Recording = {
  /** Playback for the student (video with sound, or audio only). Never uploaded. */
  url: string
  kind: 'video' | 'audio'
  mimeType: string
  durationMs: number
  /** The voice as 16 kHz WAV for feedback, or null if this browser couldn't convert it. */
  wav: Blob | null
}

const VIDEO_TYPES = ['video/webm;codecs=vp9,opus', 'video/webm;codecs=vp8,opus', 'video/webm', 'video/mp4']
const AUDIO_TYPES = ['audio/webm;codecs=opus', 'audio/webm', 'audio/mp4', 'audio/ogg;codecs=opus']
export const COUNTDOWN_SECONDS = 3

function supportedType(candidates: string[]): string | undefined {
  return candidates.find((type) => MediaRecorder.isTypeSupported(type))
}

export function recordingSupported(): boolean {
  return typeof window !== 'undefined' && !!navigator.mediaDevices?.getUserMedia && typeof MediaRecorder !== 'undefined'
}

function describeError(error: unknown): string {
  const name = (error as { name?: string } | null)?.name
  if (name === 'NotAllowedError' || name === 'SecurityError') {
    return 'Camera or mic access is blocked. Allow it from the icon in your address bar, then try again.'
  }
  if (name === 'NotFoundError' || name === 'OverconstrainedError') return 'No microphone (or camera) found. Plug one in, or switch the camera off.'
  if (name === 'NotReadableError') return 'Another app is using your camera or mic. Close it and try again.'
  return "Couldn't start recording. Try again, or use Chrome or Edge."
}

type Take = { recorder: MediaRecorder; chunks: Blob[] }

function startTake(stream: MediaStream, mimeType: string | undefined, options: MediaRecorderOptions): Take {
  const recorder = new MediaRecorder(stream, { ...options, ...(mimeType ? { mimeType } : {}) })
  const chunks: Blob[] = []
  recorder.addEventListener('dataavailable', (event) => {
    if (event.data.size > 0) chunks.push(event.data)
  })
  recorder.start(1000)
  return { recorder, chunks }
}

function stopTake(take: Take | null): Promise<Blob | null> {
  if (!take) return Promise.resolve(null)
  const { recorder, chunks } = take
  return new Promise((resolve) => {
    const done = () => resolve(chunks.length ? new Blob(chunks, { type: recorder.mimeType }) : null)
    if (recorder.state === 'inactive') return done()
    recorder.addEventListener('stop', done, { once: true })
    recorder.stop()
  })
}

function abandon(takes: (Take | null)[]) {
  for (const take of takes) if (take && take.recorder.state !== 'inactive') take.recorder.stop()
}

/**
 * Records one spoken answer: a camera preview (optional), a 3-2-1 countdown, a hard time limit,
 * a live mic level, and the result as local playback plus a WAV of the voice. The camera and mic
 * are switched off as soon as recording stops.
 */
export function useAnswerRecorder(maxSeconds: number) {
  const [phase, setPhase] = useState<RecorderPhase>('idle')
  const [error, setError] = useState<string | null>(null)
  const [stream, setStream] = useState<MediaStream | null>(null)
  const [countdown, setCountdown] = useState(COUNTDOWN_SECONDS)
  const [elapsed, setElapsed] = useState(0)
  const [level, setLevel] = useState(0)
  const [recording, setRecording] = useState<Recording | null>(null)

  const streamRef = useRef<MediaStream | null>(null)
  const takesRef = useRef<{ full: Take | null; voice: Take | null }>({ full: null, voice: null })
  const startedAtRef = useRef(0)
  const timersRef = useRef<number[]>([])
  const meterRef = useRef<{ context: AudioContext; frame: number } | null>(null)
  const urlRef = useRef<string | null>(null)
  const stoppingRef = useRef(false)

  const clearTimers = () => {
    timersRef.current.forEach((id) => window.clearInterval(id))
    timersRef.current = []
  }

  const releaseMedia = useCallback(() => {
    clearTimers()
    if (meterRef.current) {
      cancelAnimationFrame(meterRef.current.frame)
      void meterRef.current.context.close()
      meterRef.current = null
    }
    streamRef.current?.getTracks().forEach((track) => track.stop())
    streamRef.current = null
    setStream(null)
    setLevel(0)
  }, [])

  const forgetRecording = () => {
    if (urlRef.current) URL.revokeObjectURL(urlRef.current)
    urlRef.current = null
    setRecording(null)
  }

  useEffect(
    () => () => {
      abandon([takesRef.current.full, takesRef.current.voice])
      releaseMedia()
      if (urlRef.current) URL.revokeObjectURL(urlRef.current)
    },
    [releaseMedia],
  )

  const startMeter = (media: MediaStream) => {
    try {
      const context = new AudioContext()
      const analyser = context.createAnalyser()
      analyser.fftSize = 512
      context.createMediaStreamSource(media).connect(analyser)
      const samples = new Uint8Array(analyser.fftSize)
      let last = 0
      const tick = (time: number) => {
        if (time - last > 80) {
          analyser.getByteTimeDomainData(samples)
          let sum = 0
          for (const sample of samples) sum += ((sample - 128) / 128) ** 2
          setLevel(Math.min(1, Math.sqrt(sum / samples.length) * 4))
          last = time
        }
        if (meterRef.current) meterRef.current.frame = requestAnimationFrame(tick)
      }
      meterRef.current = { context, frame: requestAnimationFrame(tick) }
    } catch {
      // The meter is a nicety; recording works without it.
    }
  }

  /** Asks for the mic (and camera) and shows the preview. */
  const open = useCallback(
    async (camera: boolean) => {
      if (!recordingSupported()) {
        setError("This browser can't record. Try Chrome, Edge or Safari on a recent version.")
        return
      }
      forgetRecording()
      setError(null)
      setPhase('starting')
      try {
        const media = await navigator.mediaDevices.getUserMedia({
          audio: { echoCancellation: true, noiseSuppression: true, channelCount: 1 },
          video: camera ? { width: { ideal: 640 }, height: { ideal: 480 }, facingMode: 'user' } : false,
        })
        streamRef.current = media
        setStream(media)
        startMeter(media)
        setPhase('ready')
      } catch (err) {
        setError(describeError(err))
        setPhase('idle')
      }
    },
    [],
  )

  const finish = useCallback(async () => {
    if (stoppingRef.current) return
    stoppingRef.current = true
    clearTimers()
    setPhase('finishing')
    const durationMs = Math.round(performance.now() - startedAtRef.current)
    const { full, voice } = takesRef.current
    const [video, audio] = await Promise.all([stopTake(full), stopTake(voice)])
    takesRef.current = { full: null, voice: null }
    releaseMedia()
    const playback = video ?? audio
    if (!playback) {
      setError('Nothing was recorded. Check your mic and try again.')
      setPhase('idle')
      stoppingRef.current = false
      return
    }
    let wav: Blob | null = null
    try {
      wav = audio ? await toSpeechWav(audio) : null
    } catch {
      wav = null
    }
    const url = URL.createObjectURL(playback)
    urlRef.current = url
    setRecording({ url, kind: video ? 'video' : 'audio', mimeType: playback.type, durationMs, wav })
    setPhase('recorded')
    stoppingRef.current = false
  }, [releaseMedia])

  /** 3-2-1, then record until stopped or the time limit. */
  const begin = useCallback(() => {
    const media = streamRef.current
    if (!media) return
    setPhase('countdown')
    setCountdown(COUNTDOWN_SECONDS)
    let left = COUNTDOWN_SECONDS
    const countdownTimer = window.setInterval(() => {
      left -= 1
      if (left > 0) {
        setCountdown(left)
        return
      }
      window.clearInterval(countdownTimer)
      try {
        const hasVideo = media.getVideoTracks().length > 0
        takesRef.current = {
          full: hasVideo ? startTake(media, supportedType(VIDEO_TYPES), { videoBitsPerSecond: 600_000, audioBitsPerSecond: 64_000 }) : null,
          voice: startTake(new MediaStream(media.getAudioTracks()), supportedType(AUDIO_TYPES), { audioBitsPerSecond: 64_000 }),
        }
      } catch {
        releaseMedia()
        setError("Couldn't start recording. Try again, or use Chrome or Edge.")
        setPhase('idle')
        return
      }
      startedAtRef.current = performance.now()
      setElapsed(0)
      setPhase('recording')
      const clock = window.setInterval(() => {
        const seconds = (performance.now() - startedAtRef.current) / 1000
        setElapsed(Math.min(seconds, maxSeconds))
        if (seconds >= maxSeconds) void finish()
      }, 250)
      timersRef.current.push(clock)
    }, 1000)
    timersRef.current.push(countdownTimer)
  }, [finish, maxSeconds, releaseMedia])

  /** Back to the start: drops the recording and switches the camera off. */
  const reset = useCallback(() => {
    abandon([takesRef.current.full, takesRef.current.voice])
    takesRef.current = { full: null, voice: null }
    releaseMedia()
    forgetRecording()
    setError(null)
    setElapsed(0)
    setPhase('idle')
  }, [releaseMedia])

  return { phase, error, stream, countdown, elapsed, level, recording, open, begin, finish, reset }
}
