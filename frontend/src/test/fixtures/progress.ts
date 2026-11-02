// Synthetic learning progress for tests (not a real student).
import type { AnalyticsReport, ProgressSummary, StudentLearning, TopicSummary } from '../../lib/types'

const topic = (overrides: Partial<TopicSummary>): TopicSummary => ({
  slug: 'machine-learning/supervised-learning',
  name: 'Supervised Learning',
  domain: 'Machine Learning',
  sections: { lesson: 'done', playground: 'done', quiz: 'done', interview: 'started' },
  done: 3,
  total: 4,
  completion: 75,
  completed: false,
  started: true,
  last_visited_at: '2026-10-28T09:00:00Z',
  last_section: 'interview',
  quiz_attempts: 2,
  quiz_best: 100,
  quiz_last: 86,
  interview_takes: 1,
  active_seconds: 1500,
  mastery: { score: 90, band: 'strong', quiz_average: 93, practice_average: null },
  ...overrides,
})

export const SUPERVISED = topic({})
export const REGRESSION = topic({
  slug: 'machine-learning/regression',
  name: 'Regression',
  sections: { lesson: 'not_started', quiz: 'done' },
  done: 1,
  total: 2,
  completion: 50,
  last_section: 'quiz',
  quiz_attempts: 1,
  quiz_best: 29,
  quiz_last: 29,
  interview_takes: 0,
  active_seconds: 600,
  mastery: { score: 29, band: 'needs_work', quiz_average: 29, practice_average: null },
})

export const SUMMARY: ProgressSummary = {
  overall_completion: 67,
  sections_done: 4,
  sections_total: 6,
  topics_completed: 0,
  topics_started: 2,
  topics: [SUPERVISED, REGRESSION],
  domains: [{ name: 'Machine Learning', done: 4, total: 6, completion: 67 }],
  continue: { ...SUPERVISED, next_section: 'interview' },
  recommended: [{ ...REGRESSION, reason: 'Boost a weak spot' }],
  recent_quizzes: [
    { topic: 'Supervised Learning', slug: SUPERVISED.slug, score_pct: 86, correct: 6, total: 7, attempt_number: 2, submitted_at: '2026-10-28T09:00:00Z' },
  ],
  quiz_average: 72,
  strengths: ['Supervised Learning'],
  weaknesses: ['Regression'],
  interview: { answers_recorded: 3, feedback_count: 2, average_score: 6.8, recent_scores: [{ score: 6.1, at: '2026-10-27T09:00:00Z' }, { score: 7.5, at: '2026-10-28T09:00:00Z' }] },
  activity: { streak_days: 3, active_days_this_week: 2, active_days_last_30: 5, last_active_at: '2026-10-28T09:00:00Z', learning_seconds: 2100, learning_seconds_last_7: 900 },
}

const response = (question_index: number, correct: boolean) => ({ question_index, prompt: `Question ${question_index + 1}?`, chosen: 0, correct, difficulty: 'easy' })

export const LEARNING: StudentLearning = {
  summary: SUMMARY,
  quiz_attempts: [
    { id: 'a2', topic: 'Supervised Learning', topic_slug: SUPERVISED.slug, attempt_number: 2, correct: 2, total: 2, score_pct: 100, duration_seconds: 80, submitted_at: '2026-10-28T09:00:00Z', responses: [response(0, true), response(1, true)] },
    { id: 'a1', topic: 'Supervised Learning', topic_slug: SUPERVISED.slug, attempt_number: 1, correct: 1, total: 2, score_pct: 50, duration_seconds: 120, submitted_at: '2026-10-27T09:00:00Z', responses: [response(0, false), response(1, true)] },
    { id: 'r1', topic: 'Regression', topic_slug: REGRESSION.slug, attempt_number: 1, correct: 0, total: 2, score_pct: 0, duration_seconds: 60, submitted_at: '2026-10-26T09:00:00Z', responses: [response(0, false), response(1, false)] },
  ],
  practice: [{ topic: 'Supervised Learning', question: 'What is supervised learning?', score: 7.5, verdict: 'Almost there', deleted: false, created_at: '2026-10-28T09:00:00Z' }],
  timeline: [{ at: '2026-10-28T09:00:00Z', topic: 'Supervised Learning', section: 'quiz', action: 'Finished' }],
}

export const REPORT: AnalyticsReport = {
  range: { start: '2026-09-29', end: '2026-10-28' },
  kpis: { students: 40, new_students: 12, active_students: 25, quiz_attempts: 90, quiz_average: 68.4, practice_answers: 30, practice_average: 6.2, needing_attention: 7, published_topics: 6, published_sections: 40, average_completion: 31, learning_seconds: 45000, learning_seconds_per_learner: 1800 },
  registrations: [{ day: '2026-10-27', count: 3 }, { day: '2026-10-28', count: 5 }],
  weekly_active: [{ week: '2026-10-20', count: 18 }, { week: '2026-10-27', count: 25 }],
  score_distribution: Array.from({ length: 10 }, (_, b) => ({ from: b * 10, to: b < 9 ? b * 10 + 9 : 100, count: b })),
  topics: [{ slug: 'machine-learning/regression', name: 'Regression', domain: 'Machine Learning', started: 20, completed: 5, completion_rate: 25, quiz_attempts: 30, quiz_average: 41.2, practice_answers: 4, practice_average: 5.1, learning_seconds: 12600 }],
  domains: [{ name: 'Machine Learning', started: 20, completed: 5, completion_rate: 25, quiz_average: 41.2 }],
  weak_topics: [{ slug: 'machine-learning/regression', name: 'Regression', domain: 'Machine Learning', started: 20, completed: 5, completion_rate: 25, quiz_attempts: 30, quiz_average: 41.2, practice_answers: 4, practice_average: 5.1, learning_seconds: 12600 }],
  cohorts: [{ name: 'Batch A', students: 40, active: 25, quiz_average: 68.4 }],
  student: null,
  filters: { domains: [{ slug: 'machine-learning', name: 'Machine Learning' }], topics: [{ slug: 'machine-learning/regression', name: 'Regression' }], cohorts: [{ id: 'c1', name: 'Batch A' }] },
}
