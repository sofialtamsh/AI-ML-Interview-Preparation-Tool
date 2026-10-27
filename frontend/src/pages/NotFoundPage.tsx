import { Compass } from 'lucide-react'

import { ButtonLink } from '../components/ui/Button'
import { EmptyState } from '../components/ui/Feedback'

export default function NotFoundPage() {
  return (
    <div className="grid min-h-dvh place-items-center">
      <EmptyState
        icon={<Compass className="size-6" />}
        title="This page doesn't exist"
        action={<ButtonLink to="/">Back to start</ButtonLink>}
      >
        The link may be broken, or the page may have moved.
      </EmptyState>
    </div>
  )
}
