import type { LessonEvent, Step } from '../lesson/types'
import type { Narration, Ticker } from '../player/engine'

const streams = import.meta.glob<{ default: LessonEvent[] }>('../../../shared/streams/*.json', {
  eager: true,
})

/** The SSE events mock mode sends for a fixture (shared/streams, made by the server). */
export function streamOf(name: string): LessonEvent[] {
  const found = streams[`../../../shared/streams/${name}.json`]
  if (!found) throw new Error(`no shared stream ${name}`)
  return found.default
}

export const STREAM_NAMES = Object.keys(streams).map((p) =>
  p.split('/').pop()!.replace('.json', ''),
)

export function stepsOf(name: string): Step[] {
  return streamOf(name).flatMap((e) => (e.event === 'step' ? [e.data] : []))
}

/** Audio that plays on a fake clock. Duration per URL; unknown URLs last `defaultDuration`. */
export class FakeNarration implements Narration {
  durations = new Map<string, number | null>()
  defaultDuration = 2
  refusePlay = false
  loads: (string | null)[] = []
  rate = 1
  private time = 0
  private duration: number | null = null
  private playing = false
  private done = false

  load(url: string | null) {
    this.loads.push(url)
    this.time = 0
    this.playing = false
    this.done = false
    this.duration = url === null ? null : (this.durations.get(url) ?? this.defaultDuration)
    return Promise.resolve(this.duration)
  }
  play(rate: number) {
    if (this.refusePlay || this.duration === null) return Promise.resolve(false)
    this.rate = rate
    this.playing = true
    return Promise.resolve(true)
  }
  pause() {
    this.playing = false
  }
  stop() {
    this.playing = false
  }
  setRate(rate: number) {
    this.rate = rate
  }
  currentTime() {
    return this.time
  }
  ended() {
    return this.done
  }
  failed() {
    return false
  }
  level() {
    return this.playing ? 0.6 : 0
  }
  get isPlaying() {
    return this.playing
  }
  /** Wall-clock seconds pass. */
  advance(seconds: number) {
    if (!this.playing || this.duration === null) return
    this.time = Math.min(this.duration, this.time + seconds * this.rate)
    if (this.time >= this.duration) {
      this.playing = false
      this.done = true
    }
  }
}

/** A ticker driven by hand; `run` also moves the fake audio clock. */
export function manualClock(narration?: FakeNarration) {
  let frame: ((now: number) => void) | null = null
  let now = 0
  const ticker: Ticker = (f) => {
    frame = f
    f(now)
    return () => {
      if (frame === f) frame = null
    }
  }
  return {
    ticker,
    get running() {
      return frame !== null
    },
    /** Let `seconds` of wall time pass in 50 ms frames, flushing promises in between. */
    async run(seconds: number) {
      const frames = Math.round(seconds / 0.05)
      for (let i = 0; i < frames; i++) {
        now += 50
        narration?.advance(0.05)
        frame?.(now)
        await flush()
      }
    },
  }
}

export async function flush() {
  for (let i = 0; i < 3; i++) await Promise.resolve()
}
