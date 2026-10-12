import { createSseParser } from './sse'
import type { LessonEvent, LessonRequest } from './types'

const EVENTS = new Set(['meta', 'step', 'done', 'error'])

export class StreamError extends Error {
  readonly code: 'bad_request' | 'server' | 'network'

  constructor(code: StreamError['code'], options?: ErrorOptions) {
    super(code, options)
    this.code = code
  }
}

/** POST /lessons and call `onEvent` for every SSE event as it arrives. */
export async function streamLesson(
  request: LessonRequest,
  onEvent: (event: LessonEvent) => void,
  signal?: AbortSignal,
  fetchImpl: typeof fetch = fetch,
): Promise<void> {
  let response: Response
  try {
    response = await fetchImpl('/lessons', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', Accept: 'text/event-stream' },
      body: JSON.stringify(request),
      signal,
    })
  } catch (error) {
    if (signal?.aborted) return
    throw new StreamError('network', { cause: error })
  }
  if (!response.ok || !response.body) {
    throw new StreamError(response.status === 422 ? 'bad_request' : 'server')
  }

  const parser = createSseParser(({ event, data }) => {
    if (EVENTS.has(event)) onEvent({ event, data: JSON.parse(data) } as LessonEvent)
  })
  const reader = response.body.pipeThrough(new TextDecoderStream()).getReader()
  try {
    for (;;) {
      const { value, done } = await reader.read()
      if (done) break
      parser.push(value)
    }
    parser.end()
  } catch (error) {
    if (signal?.aborted) return
    throw new StreamError('network', { cause: error })
  }
}
