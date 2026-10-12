import { act, fireEvent, render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import App from './App'
import type { LessonEvent } from './lesson/types'
import { FakeNarration, flush, manualClock, streamOf } from './test/fakes'

/** A fetch whose SSE body is written by the test, event by event. */
function controllableFetch() {
  let controller!: ReadableStreamDefaultController<Uint8Array>
  const body = new ReadableStream<Uint8Array>({ start: (c) => void (controller = c) })
  const encoder = new TextEncoder()
  return {
    fetchImpl: async () => new Response(body, { headers: { 'Content-Type': 'text/event-stream' } }),
    async send(event: LessonEvent) {
      controller.enqueue(
        encoder.encode(`event: ${event.event}\ndata: ${JSON.stringify(event.data)}\n\n`),
      )
      await act(flush)
      await act(flush)
    },
  }
}

async function setup() {
  const narration = new FakeNarration()
  const clock = manualClock(narration)
  const server = controllableFetch()
  render(<App narration={narration} ticker={clock.ticker} fetchImpl={server.fetchImpl} />)
  await screen.findByRole('img', { name: 'Scribbly' })
  return { narration, clock, server }
}

const board = () => document.querySelector('svg.board')!

describe('App', () => {
  it('renders the title and an empty board', async () => {
    await setup()
    expect(screen.getByRole('heading', { name: 'Scribbly' })).toBeInTheDocument()
    expect(board().getAttribute('data-status')).toBe('idle')
  })

  it('writes the problem and its givens at once, then plays steps as they stream', async () => {
    const { clock, server } = await setup()
    fireEvent.click(screen.getByRole('button', { name: 'Series circuit' }))
    await act(() => clock.run(0.5))

    const intro = document.querySelector('.board-intro')!
    expect(intro.getAttribute('data-visible')).toBe('true')
    expect(intro.querySelector('[data-prim="intro-title"]')?.textContent).toBe('Problem')
    expect(screen.getByText('Scribbly is preparing the lesson…')).toBeInTheDocument()
    expect(screen.getByTestId('mascot').getAttribute('data-state')).toBe('drawing')
    await act(() => clock.run(12))
    expect(intro.querySelector('[data-prim="intro-given-0"]')?.textContent).toBe('R1 = 100 Ω')
    expect(screen.getByTestId('mascot').getAttribute('data-state')).toBe('thinking')

    const events = streamOf('circ_series')
    await server.send(events[0])
    await server.send(events[1])
    expect(board().getAttribute('data-step')).toBe('s1')
    expect(board().getAttribute('data-stage')).toBe('playing')
    expect(intro.getAttribute('data-visible')).toBe('false')
    expect(document.querySelector('.sub-en')?.textContent).toMatch(/^Three resistors in series/)
    expect(document.querySelector('.sub-second')?.textContent).toMatch(/^Uchta rezistor/) // uz
  })

  it('switches the second subtitle line and pauses', async () => {
    const { clock, server } = await setup()
    fireEvent.click(screen.getByRole('button', { name: 'Series circuit' }))
    const events = streamOf('circ_series')
    await server.send(events[0])
    await server.send(events[1])

    fireEvent.change(screen.getByRole('combobox', { name: 'Subtitles' }), {
      target: { value: 'ru' },
    })
    expect(document.querySelector('.sub-second')?.textContent).toMatch(/^Три резистора/)

    fireEvent.click(screen.getByRole('button', { name: /Pause/ }))
    await act(() => clock.run(0.2))
    expect(screen.getByRole('button', { name: /Play/ })).toBeInTheDocument()
  })

  it('asks a number checkpoint and checks the typed answer', async () => {
    const { clock, server } = await setup()
    fireEvent.click(screen.getByRole('button', { name: 'Series circuit' }))
    const events = streamOf('circ_series')
    const checkpoint = events.find((e) => e.event === 'step' && e.data.checkpoint)!
    await server.send(events[0])
    await server.send(checkpoint)
    await act(() => clock.run(8))

    fireEvent.change(screen.getByLabelText('Your answer'), { target: { value: '300' } })
    fireEvent.click(screen.getByRole('button', { name: 'Check' }))
    expect(screen.getByText('Correct!')).toBeInTheDocument()
    expect(screen.getByTestId('mascot').getAttribute('data-state')).toBe('happy')
  })

  it('shows a readable error when the server cannot be reached', async () => {
    const narration = new FakeNarration()
    const clock = manualClock(narration)
    const offline = async () => Promise.reject(new TypeError('Failed to fetch'))
    render(<App narration={narration} ticker={clock.ticker} fetchImpl={offline} />)

    fireEvent.click(screen.getByRole('button', { name: "Gauss's law" }))
    await act(flush)
    expect(screen.getByText(/Cannot reach the Scribbly server/)).toBeInTheDocument()
  })

  it('explains missing audio and keeps the narration visible when English subtitles are off', async () => {
    const { server } = await setup()
    fireEvent.click(screen.getByRole('button', { name: 'Series circuit' }))
    fireEvent.click(screen.getByRole('checkbox', { name: 'EN' }))
    const events = streamOf('circ_series')
    await server.send(events[0])
    const event = events[1]
    if (event.event !== 'step') throw new Error('expected a step')
    await server.send({ ...event, data: { ...event.data, audio_url: null } })
    expect(screen.getByText(/Audio unavailable for this step/)).toBeInTheDocument()
    expect(document.querySelector('.sub-en')?.textContent).toBe(event.data.say)
  })
})
