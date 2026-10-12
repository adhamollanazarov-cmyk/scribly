// What the board shows at one moment: every primitive drawn so far, how much of it is
// drawn, erase fades, and where the pen is. Pure, so playback can be tested without a DOM.

import type { Primitive, XY } from '../lesson/types'
import { boxOf, penAt, unionBox, type Box } from './geometry'
import { progressAt, type Schedule } from './schedule'

export interface DrawnPrim {
  prim: Primitive
  progress: number
  opacity: number
  /** Box around the target of a highlight / mark_wrong. */
  target: Box | null
}

export interface Frame {
  prims: DrawnPrim[]
  pen: XY | null
}

/** The step being drawn: its schedule and the narration clock (seconds). */
export interface Playhead {
  schedule: Schedule | null
  t: number
}

const TARGETED = new Set(['highlight', 'mark_wrong', 'erase'])

/**
 * Steps before `index` are complete; step `index` is drawn up to `playhead`
 * (null = not started). An index past the last step shows everything.
 */
export function boardFrame(
  steps: readonly { draw: Primitive[] }[],
  index: number,
  playhead: Playhead | null,
): Frame {
  const drawn: DrawnPrim[] = []
  const byId = new Map<string, DrawnPrim>()
  const byGroup = new Map<string, DrawnPrim[]>()
  let pen: XY | null = null

  const targetsOf = (id: string) => byGroup.get(id) ?? (byId.has(id) ? [byId.get(id)!] : [])

  steps.slice(0, index + 1).forEach((step, s) => {
    step.draw.forEach((prim, i) => {
      const progress = stepProgress(s === index ? playhead : 'done', i)
      if (progress <= 0) return
      const entry: DrawnPrim = { prim, progress, opacity: 1, target: null }
      if ('target_id' in prim && TARGETED.has(prim.type)) {
        const targets = targetsOf(prim.target_id)
        if (prim.type === 'erase') {
          for (const t of targets) t.opacity = Math.min(t.opacity, 1 - progress)
        } else {
          entry.target = unionBox(targets.flatMap((t) => boxOf(t.prim) ?? []))
        }
      }
      drawn.push(entry)
      byId.set(prim.id, entry)
      if (prim.group) byGroup.set(prim.group, [...(byGroup.get(prim.group) ?? []), entry])
      if (progress < 1) pen = penAt(prim, progress, entry.target) ?? pen
    })
  })
  return { prims: drawn, pen }
}

function stepProgress(playhead: Playhead | null | 'done', i: number): number {
  if (playhead === 'done') return 1
  if (!playhead?.schedule) return 0
  const slot = playhead.schedule.slots[i]
  return slot ? progressAt(slot, playhead.t) : 0
}
