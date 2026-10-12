import type { MascotState } from '../mascot/states'
import type { PlayerState } from './engine'

/** What Scribbly is doing, from the player state and whether a stroke is being drawn now. */
export function mascotState(s: PlayerState, drawingNow: boolean): MascotState {
  if (s.status === 'idle' || s.status === 'finished') return 'idle'
  if (s.status === 'error') return 'encouraging'
  if (s.paused) return 'idle'
  if (s.stage === 'answer') return 'listening'
  if (s.stage === 'feedback') return s.feedback?.correct ? 'happy' : 'encouraging'
  if (drawingNow) return 'drawing'
  if (s.stage === 'playing') {
    return s.schedule && s.t < s.schedule.length ? 'talking' : 'idle'
  }
  return 'thinking' // waiting for the next step, or loading its audio
}
