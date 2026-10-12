// Strict expected failures for medium findings intentionally left open by the
// highs-only review. An unexpected pass fails: remove `.fails` when fixing them.
import { afterEach, expect, it, vi } from 'vitest'
import { buildSchedule } from './board/schedule'
import { LessonPlayer } from './player/engine'
import { animationFrameTicker } from './player/narration'
import { FakeNarration, flush, stepsOf } from './test/fakes'

afterEach(() => vi.unstubAllGlobals())

it.fails('M1: catches the drawing up when audio ends in a background tab', async () => {
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
  expect(player.getState().t).toBeGreaterThanOrEqual(2) // currently 0.1 s
})

it.fails('M2: fits dense strokes within a short narration', () => {
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
  expect(schedule.drawEnd).toBeLessThanOrEqual(1) // 25 × 0.08 = 2 s
})

it.fails('M3: a ticker stopped inside its callback does not schedule another frame', () => {
  let frame!: FrameRequestCallback
  const raf = vi.fn((f: FrameRequestCallback) => {
    frame = f
    return 1
  })
  vi.stubGlobal('requestAnimationFrame', raf)
  vi.stubGlobal('cancelAnimationFrame', vi.fn())
  const stop = animationFrameTicker(() => stop())
  frame(0)
  expect(raf).toHaveBeenCalledTimes(1) // currently schedules a second frame after stop
})
