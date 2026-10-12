// Text equivalent of the board for screen readers: what each step says and writes.

import { t } from '../i18n'
import type { Primitive } from '../lesson/types'

export interface TranscriptItem {
  id: string
  /** A formula, read as MathML. */
  latex?: string
  text: string
}

/** What a primitive puts on the board in words, or null for pure strokes/effects. */
export function describePrim(prim: Primitive): TranscriptItem | null {
  const { id } = prim
  switch (prim.type) {
    case 'text':
      return { id, text: prim.text }
    case 'math':
      return { id, latex: prim.latex, text: prim.label ?? '' }
    case 'symbol':
      return {
        id,
        latex: prim.symbol,
        text: prim.unit ? `${prim.meaning} [${prim.unit}]` : prim.meaning,
      }
    case 'vector':
      return { id, text: prim.label ? `${prim.name} (${prim.label})` : prim.name }
    case 'axes':
      return { id, text: `${t('transcript.axes')} ${prim.xlabel}, ${prim.ylabel}` }
    case 'mark_wrong':
      return { id, text: `${t('transcript.wrong')} ${prim.reason}` }
    case 'highlight':
    case 'erase':
    case 'template':
      return null
    default:
      return prim.label ? { id, text: prim.label } : null
  }
}

export function describeAll(prims: Primitive[]): TranscriptItem[] {
  return prims.flatMap((p) => describePrim(p) ?? [])
}
