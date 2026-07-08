import { act, renderHook, waitFor } from '@testing-library/react'

import { useAsyncData } from '@/hooks/use-async-data'

describe('useAsyncData', () => {
  it('loads data and exposes it to callers', async () => {
    const load = jest.fn().mockResolvedValue({ value: 'ready' })

    const { result } = renderHook(() =>
      useAsyncData(load, {
        initialData: { value: 'initial' },
        logScope: 'test.load',
      })
    )

    expect(result.current.loading).toBe(true)

    await waitFor(() => expect(result.current.loading).toBe(false))

    expect(result.current.data).toEqual({ value: 'ready' })
    expect(result.current.error).toBeNull()
  })

  it('records a user-facing error when loading fails', async () => {
    const consoleError = jest.spyOn(console, 'error').mockImplementation(() => {})
    const load = jest.fn().mockRejectedValue(new Error('network down'))

    try {
      const { result } = renderHook(() =>
        useAsyncData(load, {
          initialData: { value: 'initial' },
          errorMessage: 'Failed to load test data.',
          logScope: 'test.load',
        })
      )

      await waitFor(() => expect(result.current.loading).toBe(false))

      expect(result.current.data).toEqual({ value: 'initial' })
      expect(result.current.error).toBe('network down')
    } finally {
      consoleError.mockRestore()
    }
  })

  it('can reload data on demand', async () => {
    const load = jest
      .fn()
      .mockResolvedValueOnce({ value: 'first' })
      .mockResolvedValueOnce({ value: 'second' })

    const { result } = renderHook(() =>
      useAsyncData(load, {
        initialData: { value: 'initial' },
        logScope: 'test.load',
      })
    )

    await waitFor(() => expect(result.current.data).toEqual({ value: 'first' }))

    await act(async () => {
      await result.current.reload()
    })

    expect(result.current.data).toEqual({ value: 'second' })
  })
})
