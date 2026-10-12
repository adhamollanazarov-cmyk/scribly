// Scribbly's movement in the overlay: a small pure state machine. The lesson says what it
// wants Scribbly to do and where ("want"); the machine decides how to get there (pop in,
// fly over, then act) and how to leave. Timers live in the component, not here.

import type { MascotState } from '../mascot/states'
import { distance, type Point } from './geometry'

export type Activity =
  'draw' | 'talk' | 'point' | 'listen' | 'think' | 'happy' | 'encourage' | 'idle'
export type Motion = 'hidden' | 'appear' | 'fly' | 'disappear' | Activity

export interface MotionState {
  motion: Motion
  /** Pencil-tip position in overlay-window DIP (the destination while flying). */
  at: Point
  /** What to do once the pop-in or flight is over. */
  pending: { activity: Activity; at: Point } | null
}

export type MotionEvent =
  | { type: 'summon'; from: Point }
  | { type: 'want'; activity: Activity; at: Point }
  | { type: 'arrived' }
  | { type: 'dismiss' }
  | { type: 'gone' }

/** A move longer than this is a flight, not a step. */
export const FLY_DISTANCE = 140
// Keep in sync with the animation lengths in mascot/scribbly.css.
export const APPEAR_MS = 450
export const FLY_MS = 700
export const DISAPPEAR_MS = 350

export const HIDDEN: MotionState = { motion: 'hidden', at: [0, 0], pending: null }

const ACTIVITIES = new Set<Motion>([
  'draw',
  'talk',
  'point',
  'listen',
  'think',
  'happy',
  'encourage',
  'idle',
])

function isActive(motion: Motion): motion is Activity {
  return ACTIVITIES.has(motion)
}

/** Go to `activity` at `at`, flying when it is far (the pen moving along a stroke is not). */
function goTo(from: MotionState, activity: Activity, at: Point): MotionState {
  const far = distance(from.at, at) > FLY_DISTANCE
  const continuingStroke = from.motion === 'draw' && activity === 'draw'
  if (far && !continuingStroke) return { motion: 'fly', at, pending: { activity, at } }
  if (from.motion === activity && from.at[0] === at[0] && from.at[1] === at[1]) return from
  return { motion: activity, at, pending: null }
}

export function nextMotion(s: MotionState, e: MotionEvent): MotionState {
  switch (e.type) {
    case 'summon':
      return s.motion === 'hidden' ? { motion: 'appear', at: e.from, pending: null } : s
    case 'dismiss':
      return s.motion === 'hidden' || s.motion === 'disappear'
        ? s
        : { motion: 'disappear', at: s.at, pending: null }
    case 'gone':
      return s.motion === 'disappear' ? { ...s, motion: 'hidden' } : s
    case 'arrived':
      if (s.motion === 'appear') {
        return s.pending ? goTo(s, s.pending.activity, s.pending.at) : { ...s, motion: 'think' }
      }
      if (s.motion === 'fly') {
        return s.pending ? { motion: s.pending.activity, at: s.at, pending: null } : s
      }
      return s
    case 'want': {
      const want = { activity: e.activity, at: e.at }
      if (s.motion === 'appear') return { ...s, pending: want }
      // Retarget the flight; the arrival timer keeps running.
      if (s.motion === 'fly') return { motion: 'fly', at: e.at, pending: want }
      return isActive(s.motion) ? goTo(s, e.activity, e.at) : s
    }
  }
}

/** The lesson's wish for Scribbly, from the board mood. */
export function activityFor(mood: MascotState, pointing: boolean): Activity {
  switch (mood) {
    case 'drawing':
      return pointing ? 'point' : 'draw'
    case 'talking':
      return 'talk'
    case 'listening':
      return 'listen'
    case 'thinking':
      return 'think'
    case 'happy':
      return 'happy'
    case 'encouraging':
      return 'encourage'
    default:
      return 'idle'
  }
}

const POSE: Record<Motion, MascotState> = {
  hidden: 'idle',
  appear: 'appearing',
  fly: 'flying',
  disappear: 'disappearing',
  draw: 'drawing',
  talk: 'talking',
  point: 'pointing',
  listen: 'listening',
  think: 'thinking',
  happy: 'happy',
  encourage: 'encouraging',
  idle: 'idle',
}

/** How Scribbly's art shows a motion. */
export function poseFor(motion: Motion): MascotState {
  return POSE[motion]
}
