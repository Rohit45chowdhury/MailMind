import { useCallback, useState } from 'react'
import { getErrorMessage } from '../api/axios.js'

/** Wraps an API function with loading / error / data state. */
export default function useRequest(fn) {
  const [state, set] = useState({ loading: false, error: '', data: null })
  const run = useCallback(async (...args) => {
    set({ loading: true, error: '', data: null })
    try {
      const data = await fn(...args)
      set({ loading: false, error: '', data })
      return data
    } catch (e) {
      set({ loading: false, error: getErrorMessage(e), data: null })
      return null
    }
  }, [fn])
  const reset = useCallback(() => set({ loading: false, error: '', data: null }), [])
  const fail = useCallback((error) => set({ loading: false, error, data: null }), [])
  return { ...state, run, reset, fail }
}
