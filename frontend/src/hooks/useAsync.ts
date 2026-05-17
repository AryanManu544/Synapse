import { useCallback, useEffect, useState } from 'react'

export type AsyncState<T> =
  | { status: 'idle' | 'loading' }
  | { status: 'success'; data: T }
  | { status: 'error'; message: string }

export function useAsync<T>(loader: () => Promise<T>) {
  const [state, setState] = useState<AsyncState<T>>({ status: 'idle' })
  const [reloadKey, setReloadKey] = useState(0)

  const reload = useCallback(() => {
    setReloadKey((key) => key + 1)
  }, [])

  useEffect(() => {
    let cancelled = false

    async function run() {
      setState({ status: 'loading' })
      try {
        const data = await loader()
        if (!cancelled) {
          setState({ status: 'success', data })
        }
      } catch (error) {
        if (!cancelled) {
          const message = error instanceof Error ? error.message : 'Something went wrong'
          setState({ status: 'error', message })
        }
      }
    }

    void run()

    return () => {
      cancelled = true
    }
    // loader is intentionally stable per page (inline arrow in useAsync call site)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [reloadKey])

  return { state, reload }
}
