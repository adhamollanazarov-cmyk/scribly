import { describe, expect, it } from 'vitest'
import { markerPlace, mouthShape, poseOf } from './pose'
import { MASCOT_STATES } from './states'

describe('Scribbly state → pose', () => {
  it.each([
    // [state, eyes, mouth, grip, arm, legs, effect] — docs/brand/scribbly-sheet.png
    ['appearing', 'open', 'open', 'hold', 'wave', 'tuck', 'burst'],
    ['flying', 'open', 'open', 'hold', 'back', 'tuck', 'trail'],
    ['drawing', 'open', 'smile', 'draw', 'down', 'stand', 'none'],
    ['talking', 'open', 'smile', 'hold', 'open', 'stand', 'rays'],
    ['pointing', 'open', 'open', 'draw', 'point', 'stand', 'rays'],
    ['thinking', 'up', 'wavy', 'hold', 'chin', 'stand', 'thought'],
    ['happy', 'happy', 'grin', 'hold', 'wave', 'tuck', 'sparkle'],
    ['encouraging', 'wink', 'open', 'hold', 'thumb', 'stand', 'rays'],
    ['idle', 'open', 'smile', 'hold', 'down', 'stand', 'none'],
    ['disappearing', 'wink', 'open', 'hold', 'wave', 'stand', 'bubbles'],
    ['listening', 'open', 'o', 'hold', 'ear', 'stand', 'waves'],
  ] as const)('%s → eyes %s, mouth %s, grip %s, arm %s, legs %s, effect %s', (state, ...want) => {
    const p = poseOf(state)
    expect([p.eyes, p.mouth, p.grip, p.arm, p.legs, p.effect]).toEqual(want)
  })

  it('has a pose for every state', () => {
    for (const state of MASCOT_STATES) expect(poseOf(state)).toBeDefined()
  })

  it('blinks in idle and never with closed eyes', () => {
    expect(poseOf('idle').blinks).toBe(true)
    expect(poseOf('happy').blinks).toBe(false)
    expect(poseOf('encouraging').blinks).toBe(false)
  })

  it('puts the marker tip on the pen only while drawing or pointing', () => {
    for (const state of MASCOT_STATES) {
      const place = markerPlace(poseOf(state).grip)
      const onPen = place.x === 0 && place.y === 0
      expect(onPen).toBe(state === 'drawing' || state === 'pointing')
    }
  })
})

describe('Scribbly mouth', () => {
  it('moves with the narration while talking or drawing', () => {
    for (const state of ['talking', 'drawing'] as const) {
      expect(mouthShape(poseOf(state), 0)).toEqual({ shape: 'smile', open: 0 })
      expect(mouthShape(poseOf(state), 0.3)).toEqual({ shape: 'open', open: 0.3 })
      expect(mouthShape(poseOf(state), 2)).toEqual({ shape: 'open', open: 1 })
    }
  })

  it('stays in its pose shape while listening to the student', () => {
    expect(mouthShape(poseOf('listening'), 0.8).shape).toBe('o')
  })
})
