import type { Narration, Ticker } from './engine'

const LOAD_TIMEOUT_MS = 8000

/**
 * Narration through one reused <audio> element. Lip sync reads loudness from a Web Audio
 * analyser, which may only start inside a user gesture: call `unlock()` from a click.
 * Without it the mouth just flaps while audio plays.
 */
export class BrowserNarration implements Narration {
  private audio = new Audio()
  private analyser: AnalyserNode | null = null
  private samples = new Uint8Array(512)

  constructor() {
    this.audio.preload = 'auto'
  }

  async unlock() {
    if (this.analyser || typeof AudioContext === 'undefined') return
    try {
      const context = new AudioContext()
      await context.resume()
      if (context.state !== 'running') {
        await context.close() // never route audio through a context that cannot play
        return
      }
      const source = context.createMediaElementSource(this.audio)
      const analyser = context.createAnalyser()
      analyser.fftSize = this.samples.length
      source.connect(analyser)
      analyser.connect(context.destination)
      this.analyser = analyser
    } catch {
      this.analyser = null
    }
  }

  load(url: string | null): Promise<number | null> {
    const audio = this.audio
    audio.pause()
    if (!url) return Promise.resolve(null)
    return new Promise((resolve) => {
      const finish = (duration: number | null) => {
        clearTimeout(timer)
        audio.removeEventListener('loadedmetadata', onMeta)
        audio.removeEventListener('error', onError)
        resolve(duration)
      }
      const onMeta = () => finish(Number.isFinite(audio.duration) ? audio.duration : null)
      const onError = () => finish(null)
      const timer = setTimeout(() => finish(null), LOAD_TIMEOUT_MS)
      audio.addEventListener('loadedmetadata', onMeta)
      audio.addEventListener('error', onError)
      audio.src = url
      audio.load()
    })
  }

  async play(rate: number): Promise<boolean> {
    this.audio.playbackRate = rate
    try {
      await this.audio.play()
      return true
    } catch {
      return false
    }
  }

  pause() {
    this.audio.pause()
  }

  stop() {
    this.audio.pause()
  }

  setRate(rate: number) {
    this.audio.playbackRate = rate
  }

  currentTime() {
    return this.audio.currentTime
  }

  ended() {
    return this.audio.ended
  }

  failed() {
    return this.audio.error !== null
  }

  level() {
    if (this.audio.paused) return 0
    if (!this.analyser) return 0.5 + 0.5 * Math.sin(performance.now() / 70)
    this.analyser.getByteTimeDomainData(this.samples)
    let sum = 0
    for (const v of this.samples) sum += ((v - 128) / 128) ** 2
    return Math.min(1, Math.sqrt(sum / this.samples.length) * 5)
  }
}

export const animationFrameTicker: Ticker = (frame) => {
  let id = requestAnimationFrame(function loop(now) {
    frame(now)
    id = requestAnimationFrame(loop)
  })
  return () => cancelAnimationFrame(id)
}
