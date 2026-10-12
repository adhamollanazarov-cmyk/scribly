// @vitest-environment node
import { fileURLToPath } from 'node:url'
import { build } from 'vite'
import { expect, it } from 'vitest'

it('loads the board dynamically and keeps every production JavaScript chunk below 500 kB', async () => {
  const result = await build({
    configFile: fileURLToPath(new URL('../vite.config.ts', import.meta.url)),
    logLevel: 'silent',
    build: { write: false },
  })
  const outputs = Array.isArray(result) ? result : [result]
  const chunks = outputs
    .flatMap((r) => ('output' in r ? r.output : []))
    .filter((o) => o.type === 'chunk')
  expect(chunks.some((c) => c.isDynamicEntry && c.name === 'Board')).toBe(true)
  expect(chunks.some((c) => c.name === 'katex')).toBe(true)
  for (const c of chunks) expect(Buffer.byteLength(c.code), c.fileName).toBeLessThan(500_000)
}, 30_000)
