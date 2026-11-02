import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, describe, expect, it, vi } from 'vitest'

import type { InterviewContent } from '../../lib/types'
import { DELIVERY, FEEDBACK } from '../../test/fixtures/practice'
import starter from '../../test/fixtures/starter-content.json'
import { studentView } from '../../admin/pages/content/shared'
import { InterviewSection } from '../sections/InterviewSection'
import { AnswerRecorder } from './AnswerRecorder'
import { FeedbackView } from './FeedbackView'
import { encodeWav } from './wav'

const interview = studentView('interview', (starter as Record<string, Record<string, Record<string, unknown>>>)['machine-learning/supervised-learning'].interview, []) as InterviewContent
const first = interview.questions[0]

afterEach(() => vi.unstubAllGlobals())

describe('WAV encoding', () => {
  it('writes a 16 kHz mono 16-bit PCM file', async () => {
    const wav = encodeWav(new Float32Array([0, 1, -1, 0.5]), 16_000)
    const bytes = new DataView(await wav.arrayBuffer())
    const text = (offset: number) => String.fromCharCode(...new Uint8Array(bytes.buffer, offset, 4))
    expect(wav.size).toBe(44 + 8)
    expect([text(0), text(8), text(12), text(36)]).toEqual(['RIFF', 'WAVE', 'fmt ', 'data'])
    expect(bytes.getUint16(22, true)).toBe(1) // mono
    expect(bytes.getUint32(24, true)).toBe(16_000)
    expect(bytes.getUint16(34, true)).toBe(16)
    expect([1, 2, 3].map((i) => bytes.getInt16(44 + i * 2, true))).toEqual([32767, -32768, 16383])
  })
})

describe('interview section', () => {
  it('shows the strong answer straight away in the admin preview (no practice)', async () => {
    render(<InterviewSection interview={interview} />)
    await userEvent.click(screen.getByText(first.question))
    expect(screen.getByText('Strong answer')).toBeInTheDocument()
  })

  it('hands the strong answer to the student app, which decides when to show it', async () => {
    const practice = vi.fn((_item, index: number) => <p>Practice panel {index}</p>)
    render(<InterviewSection interview={interview} practice={practice} />)
    await userEvent.click(screen.getByText(first.question))
    expect(screen.getByText('Practice panel 0')).toBeInTheDocument()
    expect(screen.queryByText('Strong answer')).not.toBeInTheDocument()
    expect(practice).toHaveBeenCalledWith(first, 0, expect.anything())
  })
})

describe('feedback view', () => {
  it('shows the score, the rubric, delivery and coaching', async () => {
    render(<FeedbackView feedback={FEEDBACK} delivery={DELIVERY} transcript="we learn from labelled examples" />)
    expect(screen.getByText('7.1')).toBeInTheDocument()
    expect(screen.getByText('Almost there')).toBeInTheDocument()
    expect(screen.getByRole('img', { name: 'Structure: 3 out of 5' })).toBeInTheDocument()
    expect(screen.getByText('141 wpm')).toBeInTheDocument()
    expect(screen.getByText('um ×3, basically')).toBeInTheDocument()
    expect(screen.getByText('1:42')).toBeInTheDocument()
    expect(screen.getByText(/train\/test split/)).toBeInTheDocument()
    expect(screen.getByText('→ Supervised learning needs labels.')).toBeInTheDocument()

    expect(screen.queryByText(FEEDBACK.better_answer)).not.toBeInTheDocument()
    await userEvent.click(screen.getByRole('button', { name: /say it like this/i }))
    expect(screen.getByText(FEEDBACK.better_answer)).toBeInTheDocument()
    await userEvent.click(screen.getByRole('button', { name: /next they might ask/i }))
    expect(screen.getByText('Hold out a test set.')).toBeInTheDocument()
  })
})

describe('answer recorder', () => {
  const renderRecorder = () =>
    render(<AnswerRecorder question="Explain overfitting." maxSeconds={180} actions={() => null} onClose={() => {}} />)

  it('explains when the browser cannot record', async () => {
    vi.stubGlobal('MediaRecorder', undefined)
    renderRecorder()
    await userEvent.click(screen.getByRole('button', { name: 'Turn on camera' }))
    expect(screen.getByRole('alert')).toHaveTextContent("can't record")
  })

  it('explains how to fix blocked camera access, and offers voice only', async () => {
    vi.stubGlobal('MediaRecorder', class {})
    vi.stubGlobal('navigator', {
      ...navigator,
      mediaDevices: { getUserMedia: vi.fn().mockRejectedValue(Object.assign(new Error('denied'), { name: 'NotAllowedError' })) },
    })
    renderRecorder()
    expect(screen.getByText(/your video stays on this device/i)).toBeInTheDocument()
    expect(screen.queryByText(/AI coach/)).not.toBeInTheDocument()
    await userEvent.click(screen.getByRole('radio', { name: /voice only/i }))
    await userEvent.click(screen.getByRole('button', { name: 'Turn on mic' }))
    expect(await screen.findByRole('alert')).toHaveTextContent('blocked')
  })
})
