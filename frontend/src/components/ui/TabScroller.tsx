import { useEffect, useRef, useState, type ReactNode } from 'react'

import { cn } from '../../lib/cn'

/** A horizontally scrolling tab row. On narrow screens it fades out at the edge while more tabs
 * are hidden, and keeps the selected tab in view. */
export function TabScroller({
  label,
  activeKey,
  fade = 'from-white',
  className,
  children,
}: {
  label: string
  activeKey: string
  fade?: string
  className?: string
  children: ReactNode
}) {
  const ref = useRef<HTMLDivElement>(null)
  const [more, setMore] = useState(false)

  useEffect(() => {
    const el = ref.current
    if (!el) return
    const update = () => setMore(el.scrollLeft + el.clientWidth < el.scrollWidth - 4)
    // Scroll only this row, horizontally, so the page's own scrolling is never disturbed.
    const tab = el.querySelector<HTMLElement>('[aria-selected="true"]')
    if (tab) {
      const start = tab.offsetLeft - el.offsetLeft
      const end = start + tab.offsetWidth
      if (start < el.scrollLeft) el.scrollLeft = Math.max(0, start - 8)
      else if (end > el.scrollLeft + el.clientWidth) el.scrollLeft = end - el.clientWidth + 8
    }
    update()
    el.addEventListener('scroll', update, { passive: true })
    window.addEventListener('resize', update)
    return () => {
      el.removeEventListener('scroll', update)
      window.removeEventListener('resize', update)
    }
  }, [activeKey])

  return (
    <div className="relative">
      <div ref={ref} role="tablist" aria-label={label} className={cn('flex gap-1 overflow-x-auto [scrollbar-width:none]', className)}>
        {children}
      </div>
      {more && <div aria-hidden className={cn('pointer-events-none absolute inset-y-0 right-0 w-12 rounded-r-2xl bg-gradient-to-l to-transparent', fade)} />}
    </div>
  )
}
