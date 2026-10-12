import { useLayoutEffect, useState } from 'react'
import type { Primitive } from '../lesson/types'
import type { Box } from './geometry'
import { clearMeasurements, measurePrimitive } from './measure'

export function useMeasurements(prims: readonly Primitive[]): ReadonlyMap<string, Box> {
  const [boxes, setBoxes] = useState<ReadonlyMap<string, Box>>(new Map())
  useLayoutEffect(() => {
    let disposed = false
    const measure = () => {
      if (disposed) return
      clearMeasurements()
      const next = new Map<string, Box>()
      for (const p of prims) {
        const box = measurePrimitive(p)
        if (box) next.set(p.id, box)
      }
      setBoxes(next)
    }
    measure() // requests any required local font faces, then measure again when loaded
    void document.fonts?.ready.then(measure)
    document.fonts?.addEventListener('loadingdone', measure)
    return () => {
      disposed = true
      document.fonts?.removeEventListener('loadingdone', measure)
    }
  }, [prims])
  return boxes
}
