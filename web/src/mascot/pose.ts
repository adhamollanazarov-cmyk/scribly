// How each mascot state looks: which eyes, mouth, arm, legs and extra effect Scribbly's
// layered art shows. Pure data so the mapping is tested without rendering.
// Art reference: docs/brand/scribbly-sheet.png.

import type { MascotState } from './states'

export type Eyes = 'open' | 'happy' | 'wink' | 'up'
export type Mouth = 'smile' | 'open' | 'grin' | 'o' | 'wavy'
/** The marker hand: `draw` puts the marker tip on the pen position, `hold` raises it. */
export type Grip = 'draw' | 'hold'
/** The free hand (the marker never changes hands). */
export type Arm = 'down' | 'wave' | 'open' | 'point' | 'thumb' | 'chin' | 'ear' | 'back'
export type Legs = 'stand' | 'tuck'
export type Effect =
  'none' | 'burst' | 'trail' | 'rays' | 'thought' | 'waves' | 'sparkle' | 'bubbles'

export interface Pose {
  eyes: Eyes
  /** Pupil offset in art units: where Scribbly looks. */
  look: readonly [number, number]
  blinks: boolean
  mouth: Mouth
  /** The mouth follows the narration loudness. */
  lipSync: boolean
  grip: Grip
  arm: Arm
  legs: Legs
  effect: Effect
}

/** Scribbly always holds the marker in this hand (on the left of the screen). */
export const MARKER_HAND = 'left'

const BASE: Pose = {
  eyes: 'open',
  look: [0, 0.5],
  blinks: true,
  mouth: 'smile',
  lipSync: true,
  grip: 'hold',
  arm: 'down',
  legs: 'stand',
  effect: 'none',
}

const POSES: Record<MascotState, Partial<Pose>> = {
  // row 1 of the sheet
  appearing: { mouth: 'open', arm: 'wave', legs: 'tuck', effect: 'burst', blinks: false },
  flying: { look: [2, 0], mouth: 'open', arm: 'back', legs: 'tuck', effect: 'trail' },
  drawing: { look: [-2, 2], grip: 'draw' },
  talking: { arm: 'open', effect: 'rays' },
  pointing: { look: [-2, 2], mouth: 'open', grip: 'draw', arm: 'point', effect: 'rays' },
  // row 2 of the sheet
  thinking: { eyes: 'up', look: [1.5, -2], mouth: 'wavy', arm: 'chin', effect: 'thought' },
  happy: { eyes: 'happy', mouth: 'grin', arm: 'wave', legs: 'tuck', effect: 'sparkle' },
  encouraging: { eyes: 'wink', mouth: 'open', arm: 'thumb', effect: 'rays', blinks: false },
  idle: {},
  disappearing: { eyes: 'wink', mouth: 'open', arm: 'wave', effect: 'bubbles', blinks: false },
  // not on the sheet: the student is answering
  listening: { look: [0, 0], mouth: 'o', arm: 'ear', effect: 'waves', lipSync: false },
}

export function poseOf(state: MascotState): Pose {
  const pose = { ...BASE, ...POSES[state] }
  // Closed eyes cannot blink.
  if (pose.eyes === 'happy') pose.blinks = false
  return pose
}

export interface MouthShape {
  shape: Mouth
  /** 0–1: how far an `open` mouth is open. */
  open: number
}

/** The mouth to draw: lip sync opens it with the narration, otherwise the pose's shape. */
export function mouthShape(pose: Pose, level: number): MouthShape {
  if (pose.lipSync && level > 0.06) return { shape: 'open', open: Math.min(1, level) }
  return { shape: pose.mouth, open: pose.mouth === 'open' ? 0.5 : 0 }
}

/** Marker tip position and barrel angle (deg, SVG) in art units; (0, 0) is the pen tip. */
export interface MarkerPlace {
  x: number
  y: number
  angle: number
}

/** `draw` keeps the tip exactly on the pen (the anchor); `hold` raises it beside the body. */
export function markerPlace(grip: Grip): MarkerPlace {
  return grip === 'draw' ? { x: 0, y: 0, angle: -53 } : { x: 6, y: -54, angle: 72 }
}
