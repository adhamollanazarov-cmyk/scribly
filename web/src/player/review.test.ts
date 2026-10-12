import { describe, expect, it, vi, afterEach } from 'vitest'
import { LessonPlayer } from './engine'
import { BrowserNarration } from './narration'
import { FakeNarration, flush, manualClock, stepsOf } from '../test/fakes'
import { checkAnswer } from './checkAnswer'

const step = stepsOf('gauss_law')[0]

describe('Phase 2 playback failure regressions', () => {
  it('continues after a media error instead of freezing the narration clock', async () => {
    class FailedAudio extends FakeNarration {
      broken = false
      failed() {
        return this.broken
      }
    }
    const narration = new FailedAudio()
    const clock = manualClock(narration)
    const player = new LessonPlayer(narration, clock.ticker)
    player.begin([])
    player.receive({ event: 'step', data: step })
    player.receive({ event: 'done', data: { id: 'test' } })
    await flush()
    await clock.run(0.5)
    narration.broken = true
    narration.pause()
    await clock.run(3)
    expect(player.getState().status).toBe('finished')
    expect(player.getState().records[step.id]).toEqual({ audio: 'none', drawn: true })
  })

  it('bounds a permanent audio stall, but tolerates brief buffering and pauses', async () => {
    const narration = new FakeNarration()
    const clock = manualClock(narration)
    const player = new LessonPlayer(narration, clock.ticker)
    player.begin([])
    player.receive({ event: 'step', data: step })
    player.receive({ event: 'done', data: { id: 'test' } })
    await flush()
    narration.pause() // network buffering: currentTime stops, ended remains false
    await clock.run(2)
    expect(player.getState().audioActive).toBe(true)
    expect(player.getState().t).toBe(0)
    player.pause()
    await clock.run(20)
    player.play()
    await flush()
    await clock.run(0.5)
    expect(player.getState().audioActive).toBe(true)
    expect(player.getState().t).toBeGreaterThan(0)
    narration.pause()
    await clock.run(12)
    expect(player.getState().status).toBe('finished')
    expect(player.getState().records[step.id]?.audio).toBe('none')
  })
})

describe('zero checkpoint correctness', () => {
  it.each(['1e-9', '-1e-9', '0.01'])('rejects %s C when the correct charge is zero', (input) => {
    expect(
      checkAnswer(
        { question: 'Net charge?', type: 'number', answer: 0, tolerance: 0.02, unit: 'C' },
        input,
      ).correct,
    ).toBe(false)
  })
  it.each(['0', '-0', '0e-9'])('accepts exact zero written as %s', (input) => {
    expect(
      checkAnswer({ question: 'Net charge?', type: 'number', answer: 0, unit: 'C' }, input).correct,
    ).toBe(true)
  })
})

describe('browser media errors', () => {
  afterEach(() => vi.unstubAllGlobals())
  it('exposes an error that arrives after metadata', async () => {
    class AudioStub extends EventTarget {
      duration = 3
      error: object | null = null
      src = ''
      pause() {}
      load() {
        this.dispatchEvent(new Event('loadedmetadata'))
      }
    }
    const audio = new AudioStub()
    vi.stubGlobal('Audio', function () {
      return audio
    })
    const narration = new BrowserNarration()
    await expect(narration.load('/audio/test.mp3')).resolves.toBe(3)
    audio.error = { code: 3 }
    audio.dispatchEvent(new Event('error'))
    expect(narration.failed()).toBe(true)
  })
})
