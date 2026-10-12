import { describe, expect, it, vi } from 'vitest'
import { streamLesson } from './client'
import { streamOf } from '../test/fakes'
import type { LessonEvent } from './types'

const request = { type: 'topic' as const, text: 'Explain Gauss law' }
const events = streamOf('gauss_law')
const encode = (events: LessonEvent[]) =>
  events.map((e) => `event: ${e.event}\ndata: ${JSON.stringify(e.data)}\n\n`).join('')
const respond = (body: string) => async () =>
  new Response(body, { headers: { 'Content-Type': 'text/event-stream' } })

describe('stream completion', () => {
  it.each([0, 1, 2])('rejects EOF after %s events without a terminal event', async (length) => {
    await expect(
      streamLesson(request, () => {}, undefined, respond(encode(events.slice(0, length)))),
    ).rejects.toMatchObject({ code: 'network' })
  })
  it('does not treat an unterminated done frame as successful completion', async () => {
    await expect(
      streamLesson(request, () => {}, undefined, respond(encode(events).trimEnd())),
    ).rejects.toMatchObject({ code: 'network' })
  })
  it.each(['done', 'error'] as const)(
    'stops reading at %s and cancels the response',
    async (kind) => {
      const cancel = vi.fn()
      const terminal: LessonEvent =
        kind === 'done' ? events.at(-1)! : { event: 'error', data: { message: 'Failed safely' } }
      const body = new ReadableStream<Uint8Array>({
        start(c) {
          c.enqueue(new TextEncoder().encode(encode([events[0], terminal, events[1]])))
        },
        cancel,
      })
      const seen: LessonEvent[] = []
      await streamLesson(
        request,
        (e) => seen.push(e),
        undefined,
        async () => new Response(body),
      )
      expect(seen).toEqual([events[0], terminal])
      expect(cancel).toHaveBeenCalledOnce()
    },
    1000,
  )
  it('does not deliver buffered events after cancellation', async () => {
    const controller = new AbortController()
    const seen: LessonEvent[] = []
    await streamLesson(
      request,
      (e) => {
        seen.push(e)
        controller.abort()
      },
      controller.signal,
      respond(encode(events)),
    )
    expect(seen).toEqual([events[0]])
  })
})
