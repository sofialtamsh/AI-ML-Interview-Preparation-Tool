import { useEffect, useState } from 'react'

/** The value, once it has stopped changing for `ms` (for search boxes). */
export function useDebounced(value: string, ms = 300) {
  const [debounced, setDebounced] = useState(value)
  useEffect(() => {
    const timer = window.setTimeout(() => setDebounced(value), ms)
    return () => window.clearTimeout(timer)
  }, [value, ms])
  return debounced
}
