'use client'

import * as React from 'react'

import { clientErrorMessage, logClientError } from '@/lib/client-log'

type UseAsyncDataOptions<T> = {
  initialData: T
  errorMessage?: string
  logScope: string
}

export function useAsyncData<T>(
  load: () => Promise<T>,
  options: UseAsyncDataOptions<T>
) {
  const [data, setData] = React.useState<T>(options.initialData)
  const [loading, setLoading] = React.useState(true)
  const [error, setError] = React.useState<string | null>(null)

  const reload = React.useCallback(async () => {
    setLoading(true)
    setError(null)

    try {
      const next = await load()
      setData(next)
      return next
    } catch (err) {
      logClientError(options.logScope, err)
      setError(clientErrorMessage(err, options.errorMessage || 'Failed to load data.'))
      throw err
    } finally {
      setLoading(false)
    }
  }, [load, options.errorMessage, options.logScope])

  React.useEffect(() => {
    let cancelled = false

    queueMicrotask(() => {
      if (cancelled) return
      setLoading(true)
      setError(null)

      load()
        .then((next) => {
          if (!cancelled) {
            setData(next)
          }
        })
        .catch((err) => {
          if (!cancelled) {
            logClientError(options.logScope, err)
            setError(clientErrorMessage(err, options.errorMessage || 'Failed to load data.'))
          }
        })
        .finally(() => {
          if (!cancelled) {
            setLoading(false)
          }
        })
    })

    return () => {
      cancelled = true
    }
  }, [load, options.errorMessage, options.logScope])

  return { data, setData, loading, error, reload }
}
