import { act, fireEvent, render, screen } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { FakeNarration, flush, manualClock, streamOf } from '../test/fakes'
import type { LessonMode, OverlayBridge, OverlayMode } from './bridge'
import { LessonOverlay } from './LessonOverlay'
import { APPEAR_MS, DISAPPEAR_MS, FLY_MS } from './motion'
import { OverlayApp } from './OverlayApp'
import { DEFAULT_SETTINGS, nextSpeed, sanitizeSettings } from './settings'

class FakeBridge implements OverlayBridge {
  listener: ((mode: OverlayMode) => void) | null = null
  selected: unknown[] = []
  interactive: boolean[] = []
  closed = 0
  onMode(listener: (mode: OverlayMode) => void) {
    this.listener = listener
    return () => {
      this.listener = null
    }
  }
  selectRegion(region: unknown) {
    this.selected.push(region)
  }
  setInteractive(on: boolean) {
    this.interactive.push(on)
  }
  closeLesson() {
    this.closed++
  }
}

const LESSON: LessonMode = {
  mode: 'lesson',
  region: { x: 200, y: 100, w: 640, h: 400 },
  imagePngBase64: 'iVBORw0KGgo=',
  settings: { ...DEFAULT_SETTINGS, speed: 1.25 },
}

/** Replays the Gauss mock stream; records the request. */
function gaussServer(demo = true) {
  const requests: { url: string; body: unknown }[] = []
  const text = streamOf('gauss_law')
    .map((e) => `event: ${e.event}\ndata: ${JSON.stringify(e.data)}\n\n`)
    .join('')
  const fetchImpl = (async (url: string, init: RequestInit) => {
    requests.push({ url, body: JSON.parse(init.body as string) })
    const headers: Record<string, string> = { 'Content-Type': 'text/event-stream' }
    if (demo) headers['X-Scribbly-Demo'] = '1'
    return new Response(text, { headers })
  }) as unknown as typeof fetch
  return { fetchImpl, requests }
}

async function setup(demo = true) {
  const bridge = new FakeBridge()
  const narration = new FakeNarration()
  const clock = manualClock(narration)
  const server = gaussServer(demo)
  const onDismiss = vi.fn()
  const view = render(
    <LessonOverlay
      lesson={LESSON}
      bridge={bridge}
      dismissed={false}
      onDismiss={onDismiss}
      narration={narration}
      ticker={clock.ticker}
      fetchImpl={server.fetchImpl}
    />,
  )
  await act(flush)
  await act(flush)
  return { bridge, narration, clock, server, onDismiss, view }
}

const mascot = () => document.querySelector('[data-motion]')
const board = () => document.querySelector('svg.board')!

describe('LessonOverlay', () => {
  beforeEach(() => {
    vi.useFakeTimers({ toFake: ['setTimeout', 'clearTimeout'] })
  })
  afterEach(() => {
    vi.useRealTimers()
  })

  it('sends the captured region once, with the voice setting, and plays the lesson', async () => {
    const { server, clock } = await setup()
    expect(server.requests).toEqual([
      {
        url: '/explain-region',
        body: { image_png_base64: LESSON.imagePngBase64, voice: 'en-US-AriaNeural' },
      },
    ])
    await act(() => clock.run(0.5))
    expect(board().getAttribute('data-status')).toBe('running')
    expect(board().getAttribute('data-step')).toBe('s1')
    expect(screen.getByRole('button', { name: /Speed 1.25×/ })).toBeInTheDocument()
  })

  it('says it is a demo lesson, in English and the subtitle language', async () => {
    await setup()
    const demo = screen.getByTestId('demo')
    expect(demo.textContent).toContain('Demo lesson')
    expect(demo.querySelector('[lang="uz"]')?.textContent).toContain('Namuna dars')
  })

  it('shows no demo notice when the server does not mark one', async () => {
    await setup(false)
    expect(screen.queryByTestId('demo')).toBeNull()
  })

  it('has subtitles and a pill, but no step list', async () => {
    const { clock } = await setup()
    await act(() => clock.run(0.5))
    expect(document.querySelector('.sub-en')?.textContent).toMatch(/point charge/)
    expect(document.querySelector('.sub-second')?.getAttribute('lang')).toBe('uz')
    expect(screen.getByRole('toolbar', { name: 'Lesson controls' })).toBeInTheDocument()
    expect(document.querySelector('.step-list')).toBeNull()
  })

  it('draws the board exactly over a large selected region', async () => {
    await setup()
    const frame = document.querySelector<HTMLElement>('.overlay-board')!
    expect(frame.style.left).toBe('200px')
    expect(frame.style.top).toBe('100px')
    expect(frame.style.width).toBe('640px')
    expect(frame.style.height).toBe('400px')
  })

  it('pops Scribbly in, then flies to the lesson', async () => {
    await setup()
    expect(mascot()?.getAttribute('data-motion')).toBe('appear')
    await act(() => vi.advanceTimersByTimeAsync(APPEAR_MS))
    expect(mascot()?.getAttribute('data-motion')).toBe('fly')
    await act(() => vi.advanceTimersByTimeAsync(FLY_MS))
    expect(mascot()?.getAttribute('data-motion')).not.toBe('fly')
  })

  it('pauses and resumes from the pill', async () => {
    const { clock } = await setup()
    await act(() => clock.run(0.5))
    fireEvent.click(screen.getByRole('button', { name: 'Pause' }))
    expect(screen.getByRole('button', { name: 'Play' })).toBeInTheDocument()
    fireEvent.click(screen.getByRole('button', { name: 'Play' }))
    expect(screen.getByRole('button', { name: 'Pause' })).toBeInTheDocument()
  })

  it('cycles the speed from the pill', async () => {
    await setup()
    fireEvent.click(screen.getByRole('button', { name: /Speed/ }))
    expect(screen.getByRole('button', { name: /Speed 1.5×/ })).toBeInTheDocument()
  })

  it('asks to close from the pill and from Esc', async () => {
    const { onDismiss } = await setup()
    fireEvent.click(screen.getByRole('button', { name: 'Close lesson' }))
    fireEvent.keyDown(window, { key: 'Escape' })
    expect(onDismiss).toHaveBeenCalledTimes(2)
  })

  it('takes clicks only over interactive parts', async () => {
    const { bridge } = await setup()
    fireEvent.mouseMove(screen.getByRole('button', { name: 'Close lesson' }))
    fireEvent.mouseMove(board())
    fireEvent.mouseMove(mascot()!)
    expect(bridge.interactive).toEqual([true, false, true])
  })
})

describe('OverlayApp', () => {
  beforeEach(() => {
    vi.useFakeTimers({ toFake: ['setTimeout', 'clearTimeout'] })
  })
  afterEach(() => {
    vi.useRealTimers()
  })

  it('selects a region by dragging and reports it to main', () => {
    const bridge = new FakeBridge()
    render(<OverlayApp bridge={bridge} />)
    act(() => bridge.listener?.({ mode: 'select' }))
    const selector = screen.getByTestId('selector')
    expect(screen.getByText(/Drag over what you want explained/)).toBeInTheDocument()

    fireEvent.pointerDown(selector, { button: 0, clientX: 300, clientY: 200 })
    fireEvent.pointerMove(selector, { clientX: 100, clientY: 50 })
    expect(screen.getByTestId('selector-rect').style.width).toBe('200px')
    fireEvent.pointerUp(selector, { clientX: 100, clientY: 50 })
    expect(bridge.selected).toEqual([{ x: 100, y: 50, w: 200, h: 150 }])
  })

  it('ignores a click without a drag, and cancels with Esc', () => {
    const bridge = new FakeBridge()
    render(<OverlayApp bridge={bridge} />)
    act(() => bridge.listener?.({ mode: 'select' }))
    const selector = screen.getByTestId('selector')
    fireEvent.pointerDown(selector, { button: 0, clientX: 300, clientY: 200 })
    fireEvent.pointerUp(selector, { clientX: 305, clientY: 203 })
    expect(bridge.selected).toEqual([])
    fireEvent.keyDown(window, { key: 'Escape' })
    expect(bridge.selected).toEqual([null])
  })
})

describe('OverlayApp lesson', () => {
  const realFetch = globalThis.fetch
  afterEach(() => {
    globalThis.fetch = realFetch
    vi.useRealTimers()
  })

  it('lets Scribbly leave before closing the window when main dismisses', async () => {
    const bridge = new FakeBridge()
    globalThis.fetch = gaussServer().fetchImpl
    render(<OverlayApp bridge={bridge} />)
    act(() => bridge.listener?.(LESSON))
    await screen.findByRole('toolbar', { name: 'Lesson controls' }) // lazy chunk loaded

    vi.useFakeTimers({ toFake: ['setTimeout', 'clearTimeout'] })
    act(() => bridge.listener?.({ mode: 'dismiss' }))
    expect(document.querySelector('[data-motion]')?.getAttribute('data-motion')).toBe('disappear')
    expect(bridge.closed).toBe(0)
    await act(() => vi.advanceTimersByTimeAsync(DISAPPEAR_MS))
    expect(bridge.closed).toBe(1)
  })
})

describe('overlay settings', () => {
  it('falls back to safe defaults for anything unknown', () => {
    expect(sanitizeSettings(null)).toEqual(DEFAULT_SETTINGS)
    expect(
      sanitizeSettings({ voice: 'evil', speed: 99, subtitles: 'de', launchAtLogin: 'yes' }),
    ).toEqual(DEFAULT_SETTINGS)
    expect(
      sanitizeSettings({
        voice: 'en-GB-SoniaNeural',
        speed: 1.5,
        subtitles: 'ru',
        launchAtLogin: true,
      }),
    ).toEqual({ voice: 'en-GB-SoniaNeural', speed: 1.5, subtitles: 'ru', launchAtLogin: true })
  })

  it('launch at login is off by default', () => {
    expect(DEFAULT_SETTINGS.launchAtLogin).toBe(false)
  })

  it('cycles speeds and wraps around', () => {
    expect(nextSpeed(0.75)).toBe(1)
    expect(nextSpeed(1.25)).toBe(1.5)
    expect(nextSpeed(1.5)).toBe(0.75)
    expect(nextSpeed(1.1)).toBe(1.25)
  })
})
