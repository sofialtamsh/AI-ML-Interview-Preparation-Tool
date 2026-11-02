/**
 * Turns a recorded microphone track into 16 kHz mono 16-bit WAV: the one format every
 * speech-to-text model accepts, small enough to upload (about 2 MB a minute).
 */

export const SPEECH_RATE = 16_000

/** Little-endian PCM WAV from samples in [-1, 1]. */
export function encodeWav(samples: Float32Array, sampleRate = SPEECH_RATE): Blob {
  const buffer = new ArrayBuffer(44 + samples.length * 2)
  const view = new DataView(buffer)
  const text = (offset: number, value: string) => {
    for (let i = 0; i < value.length; i++) view.setUint8(offset + i, value.charCodeAt(i))
  }
  text(0, 'RIFF')
  view.setUint32(4, 36 + samples.length * 2, true)
  text(8, 'WAVE')
  text(12, 'fmt ')
  view.setUint32(16, 16, true) // fmt chunk size
  view.setUint16(20, 1, true) // PCM
  view.setUint16(22, 1, true) // mono
  view.setUint32(24, sampleRate, true)
  view.setUint32(28, sampleRate * 2, true) // bytes per second
  view.setUint16(32, 2, true) // bytes per frame
  view.setUint16(34, 16, true) // bits per sample
  text(36, 'data')
  view.setUint32(40, samples.length * 2, true)
  for (let i = 0; i < samples.length; i++) {
    const s = Math.max(-1, Math.min(1, samples[i]))
    view.setInt16(44 + i * 2, s < 0 ? s * 0x8000 : s * 0x7fff, true)
  }
  return new Blob([buffer], { type: 'audio/wav' })
}

/** Decodes a MediaRecorder blob (WebM/Opus, MP4/AAC, …) and resamples it for speech. */
export async function toSpeechWav(recording: Blob): Promise<Blob> {
  const Context = window.AudioContext ?? (window as unknown as { webkitAudioContext: typeof AudioContext }).webkitAudioContext
  const context = new Context()
  try {
    const decoded = await context.decodeAudioData(await recording.arrayBuffer())
    const frames = Math.max(1, Math.ceil(decoded.duration * SPEECH_RATE))
    const offline = new OfflineAudioContext(1, frames, SPEECH_RATE)
    const source = offline.createBufferSource()
    source.buffer = decoded // a mono destination mixes every channel down
    source.connect(offline.destination)
    source.start()
    const rendered = await offline.startRendering()
    return encodeWav(rendered.getChannelData(0), SPEECH_RATE)
  } finally {
    void context.close()
  }
}
