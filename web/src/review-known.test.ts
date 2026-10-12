// Regressions for the Codex Phase 2 review mediums M1–M3 (docs/reviews/2026-10-12-phase2.md).
// They started as strict expected failures and pass since the integration fixes.
import { afterEach, expect, it, vi } from 'vitest'
import { buildSchedule } from './board/schedule'
import { LessonPlayer } from './player/engine'
import { animationFrameTicker } from './player/narration'
import { FakeNarration, flush, stepsOf } from './test/fakes'

afterEach(() => vi.unstubAllGlobals())

it('M1: catches the drawing up when audio ends in a background tab', async () => {
  const narration = new FakeNarration()
  let frame!: (now: number) => void
  const player = new LessonPlayer(narration, (f) => {
    frame = f
    return () => {}
  })
  player.begin([])
  player.receive({ event: 'step', data: stepsOf('gauss_law')[0] })
  await flush()
  frame(0)
  narration.advance(2)
  frame(10_000)
  expect(player.getState().t).toBeGreaterThanOrEqual(2) // was 0.1 s: the final audio time was lost
})

it('M2: fits dense strokes within a short narration', () => {
  const schedule = buildSchedule(
    Array.from({ length: 25 }, (_, i) => ({
      id: `a${i}`,
      type: 'arrow' as const,
      x1: 0,
      y1: 0,
      x2: 100,
      y2: 100,
      at: 0,
    })),
    1,
  )
  expect(schedule.drawEnd).toBeLessThanOrEqual(1) // was 2 s: 25 × the fixed 0.08 s minimum
})

it('M3: a ticker stopped inside its callback does not schedule another frame', () => {
  let frame!: FrameRequestCallback
  const raf = vi.fn((f: FrameRequestCallback) => {
    frame = f
    return 1
  })
  vi.stubGlobal('requestAnimationFrame', raf)
  vi.stubGlobal('cancelAnimationFrame', vi.fn())
  const stop = animationFrameTicker(() => stop())
  frame(0)
  expect(raf).toHaveBeenCalledTimes(1) // used to schedule a second frame after stop
})

it('M2: a primitive at the very end of the narration still finishes with it', () => {
  const prims = [
    { id: 'a', type: 'line' as const, x1: 0, y1: 0, x2: 800, y2: 0, at: 0 },
    { id: 'b', type: 'line' as const, x1: 0, y1: 0, x2: 800, y2: 0, at: 1 },
  ]
  const schedule = buildSchedule(prims, 3)
  expect(schedule.drawEnd).toBeLessThanOrEqual(3)
  expect(schedule.slots[1].start).toBeGreaterThan(schedule.slots[0].end - 1e-9) // one pen
})

it('M2: schedules that already fit keep their requested starts', () => {
  const prims = [
    { id: 'a', type: 'line' as const, x1: 0, y1: 0, x2: 100, y2: 0, at: 0.2 },
    { id: 'b', type: 'line' as const, x1: 0, y1: 0, x2: 100, y2: 0, at: 0.6 },
  ]
  const schedule = buildSchedule(prims, 10)
  expect(schedule.slots.map((s) => s.start)).toEqual([2, 6])
})

it('M3: stopping twice, or from outside, cancels the one pending frame', () => {
  const raf = vi.fn((): number => 7)
  const cancel = vi.fn()
  vi.stubGlobal('requestAnimationFrame', raf)
  vi.stubGlobal('cancelAnimationFrame', cancel)
  const stop = animationFrameTicker(() => {})
  stop()
  stop()
  expect(cancel).toHaveBeenCalledTimes(1)
  expect(cancel).toHaveBeenCalledWith(7)
})
