import { describe, expect, it, vi } from 'vitest'
import schema from '../../../shared/lesson.schema.json'
import { streamOf } from '../test/fakes'
import { StreamError, streamEvents, streamLesson } from './client'
import { extractGivens, formatGiven, introPrimitives, wrapText } from './intro'
import { SAMPLES } from './samples'
import { createSseParser, type SseMessage } from './sse'
import { PRIMITIVE_TYPES, type LessonEvent } from './types'

const fixtures = import.meta.glob<{ default: { source: { text: string } } }>(
  '../../../tests/fixtures/lessons/*.json',
  { eager: true },
)
const LABELS = { problem: 'Problem', topic: 'Topic', given: 'Given:' }

function sseText(events: LessonEvent[]): string {
  return events.map((e) => `event: ${e.event}\r\ndata: ${JSON.stringify(e.data)}\r\n\r\n`).join('')
}

function responseFrom(text: string, chunk: number, status = 200): Response {
  const bytes = new TextEncoder().encode(text)
  const body = new ReadableStream<Uint8Array>({
    start(controller) {
      for (let i = 0; i < bytes.length; i += chunk) controller.enqueue(bytes.slice(i, i + chunk))
      controller.close()
    },
  })
  return new Response(body, { status, headers: { 'Content-Type': 'text/event-stream' } })
}

describe('SSE parser', () => {
  it('handles CRLF, comments, multi-line data and chunks split anywhere', () => {
    const text =
      ': ping\r\n\r\nevent: meta\r\ndata: {"a":\r\ndata: 1}\r\n\r\nevent: done\ndata: {}\n\n'
    for (let size = 1; size <= text.length; size++) {
      const seen: SseMessage[] = []
      const parser = createSseParser((m) => seen.push(m))
      for (let i = 0; i < text.length; i += size) parser.push(text.slice(i, i + size))
      parser.end()
      expect(seen).toEqual([
        { event: 'meta', data: '{"a":\n1}' },
        { event: 'done', data: '{}' },
      ])
    }
  })
})

describe('streamLesson', () => {
  it('delivers every event of the mock stream in order', async () => {
    const events = streamOf('gauss_law')
    const fetchImpl = vi.fn(async () => responseFrom(sseText(events), 37))
    const seen: LessonEvent[] = []

    await streamLesson({ type: 'topic', text: 'x' }, (e) => seen.push(e), undefined, fetchImpl)

    expect(seen).toEqual(events)
    expect(fetchImpl).toHaveBeenCalledWith('/lessons', expect.objectContaining({ method: 'POST' }))
  })

  it.each([
    [422, 'bad_request'],
    [500, 'server'],
  ])('turns HTTP %s into a %s error', async (status, code) => {
    const fetchImpl = async () => responseFrom('', 1, status)
    const run = streamLesson({ type: 'topic', text: 'x' }, () => {}, undefined, fetchImpl)
    await expect(run).rejects.toMatchObject({ code })
  })

  it('reports a network error, but stays quiet when aborted', async () => {
    const failing = async () => Promise.reject(new TypeError('offline'))
    await expect(
      streamLesson({ type: 'topic', text: 'x' }, () => {}, undefined, failing),
    ).rejects.toBeInstanceOf(StreamError)

    const controller = new AbortController()
    controller.abort()
    await expect(
      streamLesson({ type: 'topic', text: 'x' }, () => {}, controller.signal, failing),
    ).resolves.toBeUndefined()
  })
})

describe('intro', () => {
  it('reads given values from a problem', () => {
    const text = SAMPLES[1].request.text
    expect(extractGivens(text).map(formatGiven)).toEqual([
      'R1 = 100 Ω',
      'R2 = 200 Ω',
      'R3 = 300 Ω',
      '9.0 V',
    ])
  })

  it('reads named, signed and scientific values', () => {
    const text =
      'A sphere has radius R = 0.10 m and total charge Q = +3.0 nC. Use epsilon_0 = 8.854e-12 F/m. ' +
      'Find E at r = 0.050 m and 0.20 m from its centre; a 2 kg block.'
    expect(extractGivens(text).map(formatGiven)).toEqual([
      'R = 0.10 m',
      'Q = +3.0 nC',
      'ε₀ = 8.854 × 10⁻¹² F/m',
      'r = 0.050 m',
      '0.20 m',
      '2 kg',
    ])
  })

  it('ignores numbers without units and digits inside names', () => {
    expect(extractGivens('Explain Gauss law for 3 cases in R2D2')).toEqual([])
  })

  it('wraps long text and marks a cut with an ellipsis', () => {
    expect(wrapText('one two three four', 9, 5)).toEqual(['one two', 'three', 'four'])
    expect(wrapText('one two three four', 9, 2)).toEqual(['one two', 'three …'])
  })

  it('writes the problem and its givens, or just the topic', () => {
    const problem = introPrimitives(SAMPLES[1].request, LABELS)
    expect(problem[0].text).toBe('Problem')
    expect(problem.map((p) => p.text)).toContain('Given:')
    expect(problem.map((p) => p.text)).toContain('R2 = 200 Ω')

    const topic = introPrimitives(SAMPLES[0].request, LABELS)
    expect(topic.map((p) => p.text)).toEqual(['Topic', "Explain Gauss's law"])
    for (const p of [...problem, ...topic]) {
      expect(p.x).toBeGreaterThanOrEqual(0)
      expect(p.y).toBeLessThan(1000)
    }
  })
})

describe('contract', () => {
  it('knows every primitive type of the shared schema', () => {
    const draw = schema.$defs.Step.properties.draw.items as { discriminator: { mapping: object } }
    expect([...PRIMITIVE_TYPES].sort()).toEqual(Object.keys(draw.discriminator.mapping).sort())
  })

  it('has samples that match golden fixtures, so mock mode serves them', () => {
    const sources = Object.values(fixtures).map((f) => f.default.source.text)
    for (const sample of SAMPLES) expect(sources).toContain(sample.request.text)
  })
})

describe('streamEvents', () => {
  it('posts any body to any path and shows the response headers before the first event', async () => {
    const events = streamOf('gauss_law')
    const fetchImpl = vi.fn(async () => {
      const response = responseFrom(sseText(events), 64)
      response.headers.set('X-Scribbly-Demo', '1')
      return response
    })
    const order: string[] = []

    await streamEvents(
      '/explain-region',
      { image_png_base64: 'AA==' },
      (e) => order.push(e.event),
      {
        fetchImpl,
        onOpen: (headers) => order.push(`open:${headers.get('X-Scribbly-Demo')}`),
      },
    )

    expect(order[0]).toBe('open:1')
    expect(order.slice(1)).toEqual(events.map((e) => e.event))
    expect(fetchImpl).toHaveBeenCalledWith(
      '/explain-region',
      expect.objectContaining({ body: '{"image_png_base64":"AA=="}' }),
    )
  })
})
