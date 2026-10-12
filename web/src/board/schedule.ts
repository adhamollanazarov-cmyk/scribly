// When each primitive of a step is drawn, in narration seconds (audio time at 1×).
// One pen: primitives are drawn one after another in list order, each starting no earlier
// than its `at` (fraction of the narration). Durations shrink so drawing ends with the audio.
// Speed is handled by the clock (it runs faster), so timing scales with speed automatically.

import type { Primitive } from '../lesson/types'
import { naturalDuration } from './geometry'

export interface Slot {
  start: number
  end: number
}

export interface Schedule {
  slots: Slot[]
  /** Narration length the schedule was fitted to. */
  length: number
  /** When the last primitive finishes. */
  drawEnd: number
}

const MIN_DURATION = 0.08
const FIT = 0.97 // finish drawing just before the narration ends

const SECONDS_PER_WORD = 0.38

/** Narration length when there is no audio (TTS failed or still unknown). */
export function estimateNarration(say: string): number {
  return say.split(/\s+/).filter(Boolean).length * SECONDS_PER_WORD + 0.6
}

interface Plan {
  naturals: number[]
  /** Shortest stroke allowed: MIN_DURATION, or less when that many strokes cannot fit. */
  minimum: number
  /** Latest start per primitive that still leaves room for the rest at `minimum`. */
  latest: number[]
}

function plan(prims: Primitive[], budget: number): Plan {
  const naturals = prims.map(naturalDuration)
  const drawn = naturals.filter((n) => n > 0).length
  const minimum = drawn ? Math.min(MIN_DURATION, budget / drawn) : 0
  const latest: number[] = []
  let rest = 0
  for (let i = prims.length - 1; i >= 0; i--) {
    if (naturals[i] > 0) rest += minimum
    latest[i] = Math.max(0, budget - rest)
  }
  return { naturals, minimum, latest }
}

function layout(prims: Primitive[], p: Plan, length: number, scale: number, packed: boolean) {
  const slots: Slot[] = []
  let pen = 0
  prims.forEach((prim, i) => {
    const requested = (prim.at ?? (packed ? 0 : i / prims.length)) * length
    const natural = p.naturals[i]
    const duration = natural === 0 ? 0 : Math.max(p.minimum, natural * scale)
    const start = Math.max(Math.min(requested, p.latest[i]), pen)
    slots.push({ start, end: start + duration })
    pen = start + duration
  })
  return slots
}

/**
 * Lay out `prims` over `length` seconds. length <= 0 means "natural pace, no narration":
 * primitives without `at` are then drawn back to back.
 * Late `at` values and dense steps are squeezed so drawing always ends with the narration.
 */
export function buildSchedule(prims: Primitive[], length: number): Schedule {
  const packed = length <= 0
  if (packed) length = prims.reduce((sum, p) => sum + naturalDuration(p), 0) / FIT
  const budget = length * FIT
  const p = plan(prims, budget)
  const fits = (slots: Slot[]) => slotsEnd(slots) <= budget + 1e-9
  let slots = layout(prims, p, length, 1, packed)
  if (!fits(slots)) {
    // Scale 0 (every stroke at `minimum`) always fits by construction of `latest`.
    let lo = 0
    let hi = 1
    for (let i = 0; i < 24; i++) {
      const mid = (lo + hi) / 2
      if (fits(layout(prims, p, length, mid, packed))) lo = mid
      else hi = mid
    }
    slots = layout(prims, p, length, lo, packed)
  }
  return { slots, length, drawEnd: slotsEnd(slots) }
}

function slotsEnd(slots: Slot[]): number {
  return slots.reduce((end, s) => Math.max(end, s.end), 0)
}

export function progressAt(slot: Slot, t: number): number {
  if (t >= slot.end) return 1
  if (t <= slot.start) return 0
  return (t - slot.start) / (slot.end - slot.start)
}

/** A step is over when both the narration and the drawing have finished. */
export function stepEnd(schedule: Schedule): number {
  return Math.max(schedule.length, schedule.drawEnd)
}
