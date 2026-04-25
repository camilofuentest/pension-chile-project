import { useState, useEffect } from 'react'

const BASE = import.meta.env.VITE_DATA_PATH ?? '/data'

/**
 * Fetches all 4 AFP datasets in parallel.
 * No component should call fetch() directly — always use this hook.
 *
 * If a dataset isn't ready yet (file missing or not valid JSON),
 * it returns null for that dataset instead of crashing everything.
 *
 * Returns: { data, loading, error }
 *   data    = { rentabilidades, comisiones, financiero, afiliados }
 *             each value is the parsed JSON, or null if unavailable
 *   loading = true while requests are in flight
 *   error   = only set if rentabilidades fails (it's the core dataset)
 */
export function useAfpData() {
  const [data, setData]       = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError]     = useState(null)

  useEffect(() => {
    let cancelled = false

    // fetchJson fetches one file and returns null instead of throwing
    // if the file is missing or not valid JSON.
    // This way one missing dataset never breaks the whole page.
    async function fetchJson(filename) {
      try {
        const r = await fetch(`${BASE}/${filename}`)
        if (!r.ok) return null
        return await r.json()
      } catch {
        return null
      }
    }

    async function fetchAll() {
      try {
        const [rentabilidades, comisiones, financiero, afiliados, meta] = await Promise.all([
          fetchJson('rentabilidades.json'),
          fetchJson('comisiones.json'),
          fetchJson('financiero.json'),
          fetchJson('afiliados.json'),
          fetchJson('meta.json'),
        ])

        if (!cancelled) {
          // rentabilidades is the core dataset — if it's missing, show an error
          if (!rentabilidades) {
            setError(new Error('No se encontró rentabilidades.json'))
          } else {
            setData({ rentabilidades, comisiones, financiero, afiliados, meta })
            setError(null)
          }
        }
      } catch (err) {
        if (!cancelled) setError(err)
      } finally {
        if (!cancelled) setLoading(false)
      }
    }

    fetchAll()
    return () => { cancelled = true }
  }, [])

  return { data, loading, error }
}
