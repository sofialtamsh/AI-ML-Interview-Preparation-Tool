import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'

import type { ContentComponent, TopicContent } from '../../../lib/types'
import { StudentVisibility } from './TopicContentPage'

function topic(published: ContentComponent[]): TopicContent {
  const all: ContentComponent[] = ['lesson', 'playground', 'video', 'python', 'quiz', 'interview', 'revision']
  return {
    topic: { id: 't1', slug: 'deep-learning/optimizers', name: 'Optimizers', domain_name: 'Deep Learning', is_pilot: true },
    may_generate: true,
    has_playground: true,
    components: all.map((component) => ({
      component,
      item_id: 'i',
      published_number: published.includes(component) ? 1 : null,
      latest: null,
      versions: [],
    })),
  } as unknown as TopicContent
}

describe('student visibility notice', () => {
  it('explains that a published playground stays hidden until the lesson is published', () => {
    render(<StudentVisibility topic={topic(['playground'])} />)
    expect(screen.getByText(/can't see this topic yet/)).toBeInTheDocument()
    expect(screen.getByRole('status')).toHaveTextContent('Published so far: Play.')
  })

  it('lists the tabs students see once the lesson is live, and suggests interview practice', () => {
    render(<StudentVisibility topic={topic(['lesson', 'quiz'])} />)
    expect(screen.getByRole('status')).toHaveTextContent('Students can see this topic in Explore, with these tabs: Learn, Quiz.')
    expect(screen.getByRole('status')).toHaveTextContent('Publish Interview prep')
  })
})
