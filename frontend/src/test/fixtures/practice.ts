// Synthetic practice feedback for tests (not from a real student or model).
import type { AnswerFeedback, Delivery } from '../../lib/types'

export const FEEDBACK: AnswerFeedback = {
  score: 7.1,
  verdict: { key: 'almost', label: 'Almost there' },
  answered_question: true,
  summary: 'You nailed the core idea.',
  criteria: [
    { key: 'technical_accuracy', label: 'Technical accuracy', score: 4, comment: 'Correct.' },
    { key: 'depth', label: 'Depth & coverage', score: 4, comment: 'Misses evaluation.' },
    { key: 'structure', label: 'Structure', score: 3, comment: 'No clear close.' },
    { key: 'communication', label: 'Communication', score: 4, comment: 'Clear.' },
  ],
  strengths: [{ point: 'Clear definition', quote: 'we learn from labelled examples' }],
  improvements: [{ point: 'Mention evaluation', how: 'Say how you test on held-out data.' }],
  key_points_covered: ['labelled data'],
  key_points_missed: ['train/test split'],
  mistakes: [{ quote: 'labels are optional', correction: 'Supervised learning needs labels.' }],
  tips: ['Open with a one-line definition.'],
  better_answer: 'Supervised learning is learning from labelled examples.',
  follow_up: { question: 'How would you evaluate it?', answer: 'Hold out a test set.' },
}

export const DELIVERY: Delivery = {
  duration_s: 102,
  words: 230,
  wpm: 141,
  pace: 'good',
  fillers: { um: 3, basically: 1 },
  filler_count: 4,
  longest_pause_s: 3.2,
  long_pauses: 1,
  opening_pause_s: 1.1,
}
