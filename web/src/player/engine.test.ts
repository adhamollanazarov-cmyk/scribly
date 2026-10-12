import { describe, expect, it } from 'vitest'
import { stepEnd } from '../board/schedule'
import type { LessonEvent, Step } from '../lesson/types'
import { FakeNarration, flush, manualClock, stepsOf, streamOf } from '../test/fakes'
import { LessonPlayer } from './engine'
import { mascotState } from './mascotState'

const gauss = streamOf('gauss_law')
const steps = stepsOf('gauss_law')

function setup() {
  const narration = new FakeNarration()
  const clock = manualClock(narration)
  const player = new LessonPlayer(narration, clock.ticker)
  return { narration, clock, player, state: () => player.getState() }
}

const stepEvent = (step: Step): LessonEvent => ({ event: 'step', data: step })

async function startWith(player: LessonPlayer, events: LessonEvent[]) {
  player.begin([])
  events.forEach((e) => player.receive(e))
  await flush()
}

describe('LessonPlayer', () => {
  it('plays step 1 while later steps are still streaming', async () => {
    const { player, narration, clock, state } = setup()
    await startWith(player, [gauss[0], stepEvent(steps[0])])

    expect(state().stage).toBe('playing')
    expect(state().index).toBe(0)
    expect(narration.isPlaying).toBe(true)

    await clock.run(3)
    expect(state().stage).toBe('waiting') // step 1 done, step 2 not here yet
    expect(state().index).toBe(1)
    expect(mascotState(state(), false)).toBe('thinking')

    player.receive(stepEvent(steps[1]))
    await flush()
    expect(state().stage).toBe('playing')
    expect(narration.loads).toEqual([steps[0].audio_url, steps[1].audio_url])
  })

  it('fits the drawing inside the narration and records both as finished', async () => {
    const { player, narration, clock, state } = setup()
    narration.durations.set(steps[1].audio_url!, 4)
    await startWith(player, [gauss[0], stepEvent(steps[1])])

    const schedule = state().schedule!
    expect(schedule.length).toBe(4)
    expect(schedule.drawEnd).toBeLessThanOrEqual(4)
    expect(schedule.slots).toHaveLength(steps[1].draw.length)

    await clock.run(2)
    expect(state().t).toBeCloseTo(2, 1) // the clock follows the audio
    expect(state().mouth).toBeGreaterThan(0)

    await clock.run(3)
    expect(state().records[steps[1].id]).toEqual({ audio: 'ended', drawn: true })
  })

  it.each([
    [0.5, 9],
    [1, 4.5],
    [1.5, 3],
  ])('at speed %s a 4 s step takes about %s s', async (speed, wall) => {
    const { player, narration, clock, state } = setup()
    narration.durations.set(steps[1].audio_url!, 4)
    player.setSpeed(speed)
    await startWith(player, [gauss[0], stepEvent(steps[1])])

    await clock.run(wall - 0.4)
    expect(state().records[steps[1].id]).toBeUndefined()
    await clock.run(0.8)
    expect(state().records[steps[1].id]?.audio).toBe('ended')
    expect(narration.rate).toBe(speed)
  })

  it('freezes audio and drawing while paused', async () => {
    const { player, narration, clock, state } = setup()
    await startWith(player, [gauss[0], stepEvent(steps[0])])
    await clock.run(0.5)
    player.pause()
    const t = state().t

    await clock.run(5)
    expect(state().t).toBe(t)
    expect(narration.isPlaying).toBe(false)
    expect(mascotState(state(), false)).toBe('idle')

    player.play()
    await flush()
    expect(narration.isPlaying).toBe(true)
    await clock.run(0.5)
    expect(state().t).toBeGreaterThan(t)
  })

  it('times a step from its words when it has no audio', async () => {
    const { player, narration, clock, state } = setup()
    await startWith(player, [gauss[0], stepEvent({ ...steps[0], audio_url: null })])

    expect(state().audioActive).toBe(false)
    expect(state().schedule!.length).toBeGreaterThan(3)
    expect(narration.isPlaying).toBe(false)
    await clock.run(stepEnd(state().schedule!) + 0.6)
    expect(state().records[steps[0].id]).toEqual({ audio: 'none', drawn: true })
  })

  it('keeps drawing on the wall clock if the browser refuses to play audio', async () => {
    const { player, narration, clock, state } = setup()
    narration.refusePlay = true
    await startWith(player, [gauss[0], stepEvent(steps[0])])

    expect(state().audioActive).toBe(false)
    await clock.run(3)
    expect(state().records[steps[0].id]?.drawn).toBe(true)
  })

  it('waits at a checkpoint, gives feedback, then continues', async () => {
    const { player, clock, state } = setup()
    const checkpoint = steps.find((s) => s.checkpoint)!
    const after = steps[steps.indexOf(checkpoint) + 1]
    await startWith(player, [gauss[0], stepEvent(checkpoint), stepEvent(after)])

    await clock.run(4)
    expect(state().stage).toBe('answer')
    expect(mascotState(state(), false)).toBe('listening')

    const wrong = (checkpoint.checkpoint!.answer + 1) % checkpoint.checkpoint!.choices!.length
    player.answer(wrong)
    expect(state().stage).toBe('feedback')
    expect(state().feedback?.correct).toBe(false)
    expect(mascotState(state(), false)).toBe('encouraging')

    await clock.run(10) // never moves on by itself
    expect(state().stage).toBe('feedback')
    player.next()
    await flush()
    expect(state().index).toBe(1)
    expect(state().stage).toBe('playing')
  })

  it('shows a happy mascot for a right answer', async () => {
    const { player, clock, state } = setup()
    const checkpoint = steps.find((s) => s.checkpoint)!
    await startWith(player, [gauss[0], stepEvent(checkpoint)])
    await clock.run(4)

    player.answer(checkpoint.checkpoint!.answer)
    expect(mascotState(state(), false)).toBe('happy')
  })

  it('jumps back to a step and replays it from the start', async () => {
    const { player, narration, clock, state } = setup()
    await startWith(player, [...gauss.slice(0, 3)])
    await clock.run(3)
    expect(state().index).toBe(1)

    player.jumpTo(0)
    await flush()
    expect(state().index).toBe(0)
    expect(state().t).toBe(0)
    expect(narration.loads.at(-1)).toBe(steps[0].audio_url)

    await clock.run(1)
    player.replayStep()
    await flush()
    expect(state().t).toBe(0)
  })

  it('finishes after the last step and the done event, then restarts on play', async () => {
    const { player, clock, state } = setup()
    await startWith(player, [gauss[0], stepEvent(steps[0]), { event: 'done', data: { id: 'x' } }])
    await clock.run(3)
    expect(state().status).toBe('finished')
    expect(clock.running).toBe(false)

    player.play()
    await flush()
    expect(state().status).toBe('running')
    expect(state().index).toBe(0)
  })

  it('draws the intro while waiting and hides it when step 1 starts', async () => {
    const { player, clock, state } = setup()
    player.begin([{ id: 'intro-title', type: 'text', x: 80, y: 120, text: 'Problem', size: 52 }])
    await clock.run(0.3)
    expect(state().intro!.t).toBeGreaterThan(0)
    expect(state().intro!.visible).toBe(true)

    player.receive(stepEvent(steps[0]))
    await flush()
    expect(state().intro!.visible).toBe(false)
  })

  it('shows a stream error when no step ever arrived', async () => {
    const { player, state } = setup()
    await startWith(player, [{ event: 'error', data: { message: 'boom' } }])

    expect(state().status).toBe('error')
    expect(state().error).toBe('boom')
    expect(state().intro?.visible).toBe(true) // the problem statement stays on the board
  })

  it('plays the steps it has when the stream fails later', async () => {
    const { player, clock, state } = setup()
    await startWith(player, [gauss[0], stepEvent(steps[0])])
    player.receive({ event: 'error', data: { message: 'lost' } })
    expect(state().status).toBe('running')

    await clock.run(3)
    expect(state().status).toBe('finished')
    expect(state().error).toBe('lost')
  })

  it('clamps the speed to 0.5–1.5', () => {
    const { player, state } = setup()
    player.setSpeed(3)
    expect(state().speed).toBe(1.5)
    player.setSpeed(0.1)
    expect(state().speed).toBe(0.5)
  })

  it('plays the whole golden lesson, every step drawn and voiced', async () => {
    const { player, clock, state } = setup()
    await startWith(player, gauss)
    for (let guard = 0; guard < 40 && state().status === 'running'; guard++) {
      await clock.run(1)
      if (state().stage === 'answer') {
        player.answer(state().steps[state().index].checkpoint!.answer)
        player.next()
        await flush()
      }
    }
    expect(state().status).toBe('finished')
    for (const step of steps) {
      expect(state().records[step.id]).toEqual({ audio: 'ended', drawn: true })
    }
  })
})
