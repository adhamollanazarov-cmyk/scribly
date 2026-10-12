// What the board shows at one moment, plus where Scribbly stands. Shared by the web board
// and the desktop overlay (which draws Scribbly in its own full-screen layer).

import { useMemo } from 'react'
import type { Step, XY } from '../lesson/types'
import type { MascotState } from '../mascot/states'
import type { PlayerState } from '../player/engine'
import { mascotState } from '../player/mascotState'
import { boardFrame, type Frame, type Playhead } from './frame'
import { penAt, viewBoxFor, type Box } from './geometry'
import { useMeasurements } from './useMeasurements'

const HOME: XY = [1440, 975] // the mascot's corner, bottom right
const ZOOM_SECONDS = 0.6

function lessonFrame(s: PlayerState, boxes: ReadonlyMap<string, Box>): Frame {
  if (s.stage === 'answer' || s.stage === 'feedback')
    return boardFrame(s.steps, s.index + 1, null, boxes)
  const playhead: Playhead | null = s.stage === 'playing' ? { schedule: s.schedule, t: s.t } : null
  return boardFrame(s.steps, s.index, playhead, boxes)
}

/** Where the last finished stroke ended: the mascot waits there between strokes. */
function lastPen(frame: Frame): XY | null {
  for (let i = frame.prims.length - 1; i >= 0; i--) {
    const { prim, progress, target, bounds } = frame.prims[i]
    const point = progress >= 1 ? penAt(prim, 1, target, bounds) : null
    if (point) return point
  }
  return null
}

function lerpBox(a: Box, b: Box, k: number): Box {
  const mix = (p: number, q: number) => p + (q - p) * k
  return { x: mix(a.x, b.x), y: mix(a.y, b.y), w: mix(a.w, b.w), h: mix(a.h, b.h) }
}

function viewFor(steps: Step[], index: number, t: number): Box {
  const current = viewBoxFor(steps[index]?.focus)
  const previous = viewBoxFor(steps[index - 1]?.focus)
  return lerpBox(previous, current, Math.min(1, t / ZOOM_SECONDS))
}

/** Everything the board shows at this moment; shared by the web board and the overlay. */
export interface BoardScene {
  frame: Frame
  introFrame: Frame | null
  /** Where the pen is drawing now, in board coordinates (null between strokes). */
  pen: XY | null
  mood: MascotState
  /** Where Scribbly stands (its pencil tip), in board coordinates. */
  mascotAt: XY
  /** The visible part of the board (zooms to each step's focus). */
  view: Box
}

export function useBoardScene(state: PlayerState): BoardScene {
  const intro = state.intro
  const prims = useMemo(
    () => [...(intro?.prims ?? []), ...state.steps.flatMap((s) => s.draw)],
    [intro?.prims, state.steps],
  )
  const boxes = useMeasurements(prims)
  const frame = lessonFrame(state, boxes)
  const introFrame = intro
    ? boardFrame([{ draw: intro.prims }], 0, { schedule: intro.schedule, t: intro.t }, boxes)
    : null
  const pen = frame.pen ?? (intro?.visible ? introFrame?.pen : null) ?? null
  const mood = mascotState(state, pen !== null)
  const resting =
    state.status !== 'running' || state.stage === 'answer' || state.stage === 'feedback'
  const mascotAt = pen ?? (resting ? HOME : (lastPen(frame) ?? HOME))
  const view = viewFor(state.steps, state.index, state.stage === 'playing' ? state.t : 1e9)
  return { frame, introFrame, pen, mood, mascotAt, view }
}

