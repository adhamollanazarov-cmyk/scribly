// Lesson playback: plays each step's audio and draws its primitives in sync.
// Steps are played as soon as they arrive, so step 1 starts while later steps still stream.
// The clock is narration time: audio.currentTime while audio plays, otherwise wall time ×
// speed. Drawing schedules are in narration time, so speed scales audio and strokes alike.

import { buildSchedule, estimateNarration, stepEnd, type Schedule } from '../board/schedule'
import type { LessonEvent, LessonMeta, Primitive, Step } from '../lesson/types'
import { checkAnswer, type AnswerResult } from './checkAnswer'

export interface Narration {
  /** Load audio; resolves to its duration in seconds, or null (no audio / failed). */
  load(url: string | null): Promise<number | null>
  /** Start or resume; false if the browser refused to play. */
  play(rate: number): Promise<boolean>
  pause(): void
  stop(): void
  setRate(rate: number): void
  currentTime(): number
  ended(): boolean
  /** Loudness 0–1 right now, for the mouth. */
  level(): number
}

/** Starts calling `frame(nowMs)` repeatedly; returns a function that stops it. */
export type Ticker = (frame: (nowMs: number) => void) => () => void

export type Status = 'idle' | 'running' | 'finished' | 'error'
export type Stage = 'waiting' | 'loading' | 'playing' | 'answer' | 'feedback'

export interface StepRecord {
  audio: 'ended' | 'none'
  drawn: boolean
}

export interface Intro {
  prims: Primitive[]
  schedule: Schedule
  t: number
  visible: boolean
}

export interface PlayerState {
  status: Status
  paused: boolean
  speed: number
  meta: LessonMeta | null
  steps: Step[]
  streamDone: boolean
  error: string | null
  index: number
  stage: Stage
  /** Narration clock of the current step, in seconds. */
  t: number
  schedule: Schedule | null
  /** Audio is playing for this step and drives the clock. */
  audioActive: boolean
  mouth: number
  feedback: AnswerResult | null
  records: Record<string, StepRecord>
  intro: Intro | null
}

export const MIN_SPEED = 0.5
export const MAX_SPEED = 1.5
const TAIL = 0.45 // pause after a step, in narration seconds
const MAX_FRAME = 0.1 // a hidden tab must not make the clock jump

export function initialState(): PlayerState {
  return {
    status: 'idle',
    paused: false,
    speed: 1,
    meta: null,
    steps: [],
    streamDone: false,
    error: null,
    index: 0,
    stage: 'waiting',
    t: 0,
    schedule: null,
    audioActive: false,
    mouth: 0,
    feedback: null,
    records: {},
    intro: null,
  }
}

export class LessonPlayer {
  private s: PlayerState = initialState()
  private snapshot: PlayerState = this.s
  private listeners = new Set<() => void>()
  private stopTicker: (() => void) | null = null
  private last: number | null = null
  private token = 0
  private narration: Narration
  private ticker: Ticker

  constructor(narration: Narration, ticker: Ticker) {
    this.narration = narration
    this.ticker = ticker
  }

  subscribe = (listener: () => void) => {
    this.listeners.add(listener)
    return () => this.listeners.delete(listener)
  }

  getState = () => this.snapshot

  /** A new lesson request: clear the board and write the intro while waiting. */
  begin(introPrims: Primitive[]) {
    this.narration.stop()
    this.token++
    const speed = this.s.speed
    this.s = { ...initialState(), status: 'running', speed }
    this.s.intro = {
      prims: introPrims,
      schedule: buildSchedule(introPrims, 0),
      t: 0,
      visible: true,
    }
    this.startTicking()
    this.emit()
  }

  receive(event: LessonEvent) {
    if (this.s.status === 'idle') return
    switch (event.event) {
      case 'meta':
        this.s.meta = event.data
        break
      case 'step':
        this.s.steps = [...this.s.steps, event.data]
        if (this.isWaitingFor(this.s.steps.length - 1)) this.startStep(this.s.index)
        break
      case 'done':
        this.s.streamDone = true
        if (this.isWaitingFor(this.s.steps.length)) this.finish()
        break
      case 'error':
        this.fail(event.data.message)
        break
    }
    this.emit()
  }

  /** The request itself failed (network, bad input). */
  fail(message: string) {
    this.s.error = message
    this.s.streamDone = true
    if (this.isWaitingFor(this.s.steps.length)) this.finish()
    this.emit()
  }

  play() {
    if (this.s.status === 'finished' && this.s.steps.length) return this.jumpTo(0)
    if (this.s.status !== 'running' || !this.s.paused) return
    this.s.paused = false
    this.last = null
    if (this.s.stage === 'playing' && this.s.audioActive && !this.narration.ended()) {
      void this.playAudio(this.token)
    }
    this.emit()
  }

  pause() {
    if (this.s.status !== 'running' || this.s.paused) return
    this.s.paused = true
    this.s.mouth = 0
    this.narration.pause()
    this.emit()
  }

  setSpeed(speed: number) {
    this.s.speed = Math.min(MAX_SPEED, Math.max(MIN_SPEED, speed))
    this.narration.setRate(this.s.speed)
    this.emit()
  }

  jumpTo(index: number) {
    if (index < 0 || index >= this.s.steps.length) return
    this.s.status = 'running'
    this.s.paused = false
    this.startTicking()
    this.startStep(index)
    this.emit()
  }

  restart() {
    this.jumpTo(0)
  }

  replayStep() {
    this.jumpTo(Math.min(this.s.index, this.s.steps.length - 1))
  }

  answer(input: number | string) {
    const checkpoint = this.s.steps[this.s.index]?.checkpoint
    if (this.s.stage !== 'answer' || !checkpoint) return
    this.s.feedback = checkAnswer(checkpoint, input)
    this.s.stage = 'feedback'
    this.emit()
  }

  /** Leave a checkpoint (answered or skipped) and go on. */
  next() {
    if (this.s.stage !== 'answer' && this.s.stage !== 'feedback') return
    this.advance(this.s.index + 1)
    this.emit()
  }

  /** Stop sound and the clock (component unmount). Listeners stay subscribed. */
  dispose() {
    this.token++
    this.stopTicker?.()
    this.stopTicker = null
    this.narration.stop()
  }

  private isWaitingFor(index: number) {
    return this.s.status === 'running' && this.s.stage === 'waiting' && this.s.index === index
  }

  private startStep(index: number) {
    const token = ++this.token
    const step = this.s.steps[index]
    this.narration.stop()
    Object.assign(this.s, {
      index,
      stage: 'loading',
      t: 0,
      schedule: null,
      audioActive: false,
      mouth: 0,
      feedback: null,
    } satisfies Partial<PlayerState>)
    if (this.s.intro) this.s.intro.visible = false
    void this.narration.load(step.audio_url).then((duration) => {
      if (token !== this.token) return
      this.s.schedule = buildSchedule(step.draw, duration ?? estimateNarration(step.say))
      this.s.stage = 'playing'
      this.s.audioActive = duration !== null
      this.last = null
      if (this.s.audioActive && !this.s.paused) void this.playAudio(token)
      this.emit()
    })
  }

  private async playAudio(token: number) {
    const ok = await this.narration.play(this.s.speed)
    if (!ok && token === this.token) {
      this.s.audioActive = false // autoplay refused: keep going on the wall clock
      this.emit()
    }
  }

  private completeStep() {
    const step = this.s.steps[this.s.index]
    const audioEnded = this.s.audioActive && this.narration.ended()
    this.s.records = {
      ...this.s.records,
      [step.id]: { audio: audioEnded ? 'ended' : 'none', drawn: true },
    }
    this.s.mouth = 0
    if (step.checkpoint) this.s.stage = 'answer'
    else this.advance(this.s.index + 1)
  }

  private advance(index: number) {
    this.narration.stop()
    this.s.feedback = null
    if (index < this.s.steps.length) return this.startStep(index)
    this.token++
    if (this.s.streamDone) return this.finish()
    Object.assign(this.s, { index, stage: 'waiting', t: 0, schedule: null, audioActive: false })
  }

  private finish() {
    this.stopTicker?.()
    this.stopTicker = null
    Object.assign(this.s, {
      status: this.s.error && !this.s.steps.length ? 'error' : 'finished',
      index: this.s.steps.length,
      stage: 'waiting',
      schedule: null,
      mouth: 0,
    } satisfies Partial<PlayerState>)
  }

  private startTicking() {
    if (this.stopTicker) return
    this.last = null
    this.stopTicker = this.ticker(this.tick)
  }

  private tick = (now: number) => {
    const dt = this.last === null ? 0 : Math.min(MAX_FRAME, (now - this.last) / 1000)
    this.last = now
    if (this.s.paused || this.s.status !== 'running') return
    let changed = false
    const intro = this.s.intro
    if (intro?.visible && intro.t < intro.schedule.drawEnd) {
      intro.t += dt * this.s.speed
      changed = true
    }
    if (this.s.stage === 'playing' && this.s.schedule) {
      const audio = this.s.audioActive && !this.narration.ended()
      this.s.t = audio
        ? Math.max(this.s.t, this.narration.currentTime())
        : this.s.t + dt * this.s.speed
      this.s.mouth = audio ? this.narration.level() : 0
      if (this.s.t >= stepEnd(this.s.schedule) + TAIL) this.completeStep()
      changed = true
    }
    if (changed) this.emit()
  }

  private emit() {
    const intro = this.s.intro && { ...this.s.intro }
    this.snapshot = { ...this.s, intro }
    for (const listener of this.listeners) listener()
  }
}
