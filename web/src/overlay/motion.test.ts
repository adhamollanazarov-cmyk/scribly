import { describe, expect, it } from 'vitest'
import { MASCOT_STATES } from '../mascot/states'
import {
  activityFor,
  FLY_DISTANCE,
  HIDDEN,
  nextMotion,
  poseFor,
  type Activity,
  type Motion,
  type MotionEvent,
  type MotionState,
} from './motion'

const CORNER = [1800, 1000] as const
const BOARD = [400, 300] as const
const NEAR = [BOARD[0] + 20, BOARD[1] + 10] as const

const run = (events: MotionEvent[], from: MotionState = HIDDEN) => events.reduce(nextMotion, from)
const at = (motion: Motion, point: readonly [number, number] = BOARD): MotionState => ({
  motion,
  at: point,
  pending: null,
})

describe('Scribbly motion state machine', () => {
  it('pops in at the corner, then thinks while the lesson is prepared', () => {
    const s = run([{ type: 'summon', from: CORNER }])
    expect(s).toEqual({ motion: 'appear', at: CORNER, pending: null })
    expect(nextMotion(s, { type: 'arrived' }).motion).toBe('think')
  })

  it('remembers what the lesson wants during the pop-in and flies there afterwards', () => {
    const s = run([
      { type: 'summon', from: CORNER },
      { type: 'want', activity: 'draw', at: BOARD },
    ])
    expect(s.motion).toBe('appear')
    expect(s.at).toEqual(CORNER)

    const flying = nextMotion(s, { type: 'arrived' })
    expect(flying).toEqual({ motion: 'fly', at: BOARD, pending: { activity: 'draw', at: BOARD } })
    expect(nextMotion(flying, { type: 'arrived' })).toEqual(at('draw'))
  })

  it('switches activity in place when the target is near', () => {
    expect(nextMotion(at('talk'), { type: 'want', activity: 'draw', at: NEAR })).toEqual(
      at('draw', NEAR),
    )
  })

  it('flies when the next target is far', () => {
    const far = [BOARD[0] + FLY_DISTANCE + 1, BOARD[1]] as const
    const s = nextMotion(at('talk'), { type: 'want', activity: 'point', at: far })
    expect(s.motion).toBe('fly')
    expect(s.pending).toEqual({ activity: 'point', at: far })
  })

  it('follows the pen along a stroke without flying, however fast it moves', () => {
    const far = [BOARD[0] + 3 * FLY_DISTANCE, BOARD[1]] as const
    expect(nextMotion(at('draw'), { type: 'want', activity: 'draw', at: far })).toEqual(
      at('draw', far),
    )
  })

  it('retargets a flight that is under way', () => {
    const flying: MotionState = {
      motion: 'fly',
      at: BOARD,
      pending: { activity: 'draw', at: BOARD },
    }
    const s = nextMotion(flying, { type: 'want', activity: 'talk', at: NEAR })
    expect(s).toEqual({ motion: 'fly', at: NEAR, pending: { activity: 'talk', at: NEAR } })
  })

  it.each<Activity>(['draw', 'talk', 'point', 'listen', 'think', 'happy', 'encourage', 'idle'])(
    'disappears from %s and is then hidden',
    (activity) => {
      const s = nextMotion(at(activity), { type: 'dismiss' })
      expect(s.motion).toBe('disappear')
      expect(nextMotion(s, { type: 'gone' }).motion).toBe('hidden')
    },
  )

  it('can be dismissed mid-flight or mid-pop-in', () => {
    expect(nextMotion(at('fly'), { type: 'dismiss' }).motion).toBe('disappear')
    expect(nextMotion(at('appear'), { type: 'dismiss' }).motion).toBe('disappear')
  })

  it('ignores lesson wishes while hidden or leaving', () => {
    const want: MotionEvent = { type: 'want', activity: 'talk', at: BOARD }
    expect(nextMotion(HIDDEN, want)).toBe(HIDDEN)
    const leaving = at('disappear')
    expect(nextMotion(leaving, want)).toBe(leaving)
    expect(nextMotion(leaving, { type: 'summon', from: CORNER })).toBe(leaving)
  })

  it('ignores stray timer events', () => {
    for (const motion of ['draw', 'talk', 'idle', 'hidden'] as const) {
      const s = at(motion)
      expect(nextMotion(s, { type: 'arrived' })).toBe(s)
      expect(nextMotion(s, { type: 'gone' })).toBe(s)
    }
    expect(nextMotion(HIDDEN, { type: 'dismiss' })).toBe(HIDDEN)
  })

  it('does not re-summon while visible', () => {
    const s = at('talk')
    expect(nextMotion(s, { type: 'summon', from: CORNER })).toBe(s)
  })

  it('keeps the same state object when nothing changes (no extra renders)', () => {
    const s = at('talk')
    expect(nextMotion(s, { type: 'want', activity: 'talk', at: BOARD })).toBe(s)
  })
})

describe('lesson mood → activity → pose', () => {
  it('maps every board mood to an activity, pointing while a highlight is drawn', () => {
    expect(activityFor('drawing', false)).toBe('draw')
    expect(activityFor('drawing', true)).toBe('point')
    expect(activityFor('talking', false)).toBe('talk')
    expect(activityFor('thinking', false)).toBe('think')
    expect(activityFor('listening', false)).toBe('listen')
    expect(activityFor('happy', false)).toBe('happy')
    expect(activityFor('encouraging', false)).toBe('encourage')
    expect(activityFor('idle', false)).toBe('idle')
  })

  it('shows every motion with a pose Scribbly can draw', () => {
    const motions: Motion[] = [
      'hidden',
      'appear',
      'fly',
      'disappear',
      'draw',
      'talk',
      'point',
      'listen',
      'think',
      'happy',
      'encourage',
      'idle',
    ]
    for (const m of motions) expect(MASCOT_STATES).toContain(poseFor(m))
    expect(poseFor('fly')).toBe('flying')
    expect(poseFor('point')).toBe('pointing')
  })
})
