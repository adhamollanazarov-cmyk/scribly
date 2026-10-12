// Minimal text/event-stream parser (POST + fetch, so EventSource cannot be used).

export interface SseMessage {
  event: string
  data: string
}

export function createSseParser(onMessage: (message: SseMessage) => void) {
  let buffer = ''
  let pendingCR = false // a chunk ended in "\r"; its "\n" may come in the next chunk

  function dispatch(block: string) {
    let event = 'message'
    const data: string[] = []
    for (const line of block.split('\n')) {
      if (line === '' || line.startsWith(':')) continue
      const colon = line.indexOf(':')
      const field = colon === -1 ? line : line.slice(0, colon)
      let value = colon === -1 ? '' : line.slice(colon + 1)
      if (value.startsWith(' ')) value = value.slice(1)
      if (field === 'event') event = value
      else if (field === 'data') data.push(value)
    }
    if (data.length) onMessage({ event, data: data.join('\n') })
  }

  return {
    push(chunk: string) {
      let text = (pendingCR ? '\r' : '') + chunk
      pendingCR = text.endsWith('\r')
      if (pendingCR) text = text.slice(0, -1)
      buffer += text.replace(/\r\n?/g, '\n')
      let end = buffer.indexOf('\n\n')
      while (end !== -1) {
        dispatch(buffer.slice(0, end))
        buffer = buffer.slice(end + 2)
        end = buffer.indexOf('\n\n')
      }
    },
    end() {
      // A trailing CR still ends a line. Only blank-line-terminated frames are
      // complete; never turn a truncated final frame into a successful `done`.
      if (pendingCR) this.push('\n')
      buffer = ''
      pendingCR = false
    },
  }
}
