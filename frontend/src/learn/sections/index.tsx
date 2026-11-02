import { BookOpen, Clapperboard, Code2, Gamepad2, MessagesSquare, NotebookPen, Zap, type LucideIcon } from 'lucide-react'
import type { ReactNode } from 'react'

import type {
  ContentComponent,
  ProgressKind,
  QuizResult,
  InterviewContent,
  Lesson,
  PlaygroundContent,
  PythonLabContent,
  QuizContent,
  RevisionContent,
  VideoContent,
} from '../../lib/types'
import { CodeLab } from './CodeLab'
import { InterviewSection, type PracticeRenderer } from './InterviewSection'
import { LessonDeck } from './LessonDeck'
import { PlaygroundSection } from './PlaygroundSection'
import { QuizSection } from './QuizSection'
import { RevisionSheet } from './RevisionSheet'
import { VideoPlayer } from './VideoPlayer'

export type ComponentKey = ContentComponent

/** Reports what the student did in a section (the student app saves it; previews pass nothing). */
export type ProgressReporter = (kind: ProgressKind, data?: Record<string, unknown>) => void
/** Saves a finished quiz and returns how it went. */
export type QuizSaver = (answers: (number | null)[], seconds: number) => Promise<QuizResult>

/** Same order as the backend's COMPONENT_ORDER: check understanding with the quiz, then say it out loud. */
export const SECTION_ORDER: ComponentKey[] = ['lesson', 'playground', 'video', 'python', 'quiz', 'interview', 'revision']

export const SECTIONS: Record<ComponentKey, { label: string; slug: string; icon: LucideIcon; blurb: string; admin: string }> = {
  lesson: { label: 'Learn', slug: 'learn', icon: BookOpen, blurb: 'Bite-size cards', admin: 'Lesson cards' },
  playground: { label: 'Play', slug: 'play', icon: Gamepad2, blurb: 'Hands-on playground', admin: 'Playground' },
  video: { label: 'Watch', slug: 'watch', icon: Clapperboard, blurb: 'Narrated explainer', admin: 'Video explainer' },
  python: { label: 'Code', slug: 'code', icon: Code2, blurb: 'Run real Python', admin: 'Python lab' },
  interview: { label: 'Interview', slug: 'interview', icon: MessagesSquare, blurb: 'Answer on camera, get scored', admin: 'Interview prep' },
  quiz: { label: 'Quiz', slug: 'quiz', icon: Zap, blurb: 'Test yourself', admin: 'Quiz' },
  revision: { label: 'Revise', slug: 'revise', icon: NotebookPen, blurb: '5-minute cheat sheet', admin: 'Revision sheet' },
}

/** Renders one component's body. Shared by the student topic page and the admin preview. */
export function SectionBody({
  component,
  body,
  audioUrl,
  after,
  practice,
  onProgress,
  onQuizFinished,
}: {
  component: ComponentKey
  body: unknown
  audioUrl?: (id: string) => string
  after?: ReactNode
  /** Spoken-answer practice for interview questions; only the student app passes it. */
  practice?: PracticeRenderer
  onProgress?: ProgressReporter
  onQuizFinished?: QuizSaver
}) {
  switch (component) {
    case 'lesson':
      return <LessonDeck lesson={body as Lesson} after={after} onProgress={onProgress} />
    case 'playground':
      return <PlaygroundSection playground={body as PlaygroundContent} onProgress={onProgress} />
    case 'video':
      return <VideoPlayer video={body as VideoContent} audioUrl={audioUrl} onProgress={onProgress} />
    case 'python':
      return <CodeLab lab={body as PythonLabContent} onProgress={onProgress} />
    case 'interview':
      return <InterviewSection interview={body as InterviewContent} practice={practice} />
    case 'quiz':
      return <QuizSection quiz={body as QuizContent} onFinish={onQuizFinished} />
    case 'revision':
      return <RevisionSheet revision={body as RevisionContent} />
  }
}
