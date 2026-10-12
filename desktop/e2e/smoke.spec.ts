// Electron smoke test: tray start, hotkey flow (via a test hook), region capture, demo lesson
// drawn over the region, Esc closes. A local stub replays the mock Gauss stream, so no
// Python server, API key or TTS is needed.
import { mkdtempSync, readFileSync } from 'node:fs'
import { createServer, type Server } from 'node:http'
import type { AddressInfo } from 'node:net'
import { tmpdir } from 'node:os'
import { join } from 'node:path'
import { _electron as electron, expect, test, type ElectronApplication } from '@playwright/test'

const ROOT = join(__dirname, '..')
const STREAM = join(ROOT, '..', 'shared', 'streams', 'gauss_law.json')

interface Received {
  image: Buffer
  voice: unknown
}

function stubServer(received: Received[]): Promise<{ server: Server; url: string }> {
  const events = JSON.parse(readFileSync(STREAM, 'utf8')) as { event: string; data: unknown }[]
  const body = events
    .map(({ event, data }) => {
      const silent = event === 'step' ? { ...(data as object), audio_url: null } : data
      return `event: ${event}\ndata: ${JSON.stringify(silent)}\n\n`
    })
    .join('')
  const server = createServer((req, res) => {
    if (req.method !== 'POST' || req.url !== '/explain-region') {
      res.writeHead(404).end()
      return
    }
    const chunks: Buffer[] = []
    req.on('data', (c: Buffer) => chunks.push(c))
    req.on('end', () => {
      const json = JSON.parse(Buffer.concat(chunks).toString('utf8'))
      received.push({ image: Buffer.from(json.image_png_base64, 'base64'), voice: json.voice })
      res.writeHead(200, { 'Content-Type': 'text/event-stream', 'X-Scribbly-Demo': '1' })
      res.end(body)
    })
  })
  return new Promise((done) =>
    server.listen(0, '127.0.0.1', () => {
      const { port } = server.address() as AddressInfo
      done({ server, url: `http://127.0.0.1:${port}` })
    }),
  )
}

type Hooks = {
  startSelection: () => void
  hasTray: () => boolean
  hotkeyRegistered: () => boolean
  overlayActive: () => boolean
}
const hooks = (app: ElectronApplication) => ({
  call: <K extends keyof Hooks>(name: K) =>
    app.evaluate(
      (_electron, key) =>
        (globalThis as unknown as { __scribblyTest: Hooks }).__scribblyTest[key as keyof Hooks](),
      name,
    ),
})

test('tray start → select a region → demo lesson over it → Esc closes', async () => {
  const received: Received[] = []
  const { server, url } = await stubServer(received)
  const app = await electron.launch({
    args: [ROOT],
    env: {
      ...process.env,
      SCRIBBLY_E2E: '1',
      SCRIBBLY_SERVER: url,
      SCRIBBLY_USER_DATA: mkdtempSync(join(tmpdir(), 'scribbly-e2e-')),
    },
  })
  try {
    const test = hooks(app)
    await expect
      .poll(() => app.evaluate(() => '__scribblyTest' in globalThis), { timeout: 15_000 })
      .toBe(true)
    // Starts hidden, as a tray app with the hotkey; launch at login stays off.
    expect(await test.call('hasTray')).toBe(true)
    expect(await test.call('hotkeyRegistered')).toBe(true)
    expect(await app.evaluate(({ BrowserWindow }) => BrowserWindow.getAllWindows().length)).toBe(0)
    expect(await app.evaluate(({ app }) => app.getLoginItemSettings().openAtLogin)).toBe(false)

    // The hotkey's action: one dimmed selector per display.
    const first = app.waitForEvent('window')
    await test.call('startSelection')
    const page = await first
    await expect(page.getByTestId('selector')).toBeVisible()

    // Node never reaches the page (nodeIntegration off, context isolation on).
    const leaked = await page.evaluate(() => {
      const w = window as unknown as Record<string, unknown>
      return ['require', 'process', 'module', 'Buffer', 'ipcRenderer'].filter(
        (name) => typeof w[name] !== 'undefined',
      )
    })
    expect(leaked).toEqual([])
    expect(await page.evaluate(() => Object.keys(window.scribbly ?? {}).sort())).toEqual([
      'closeLesson',
      'onMode',
      'selectRegion',
      'setInteractive',
    ])
    // CSP: an injected inline script must not run.
    expect(
      await page.evaluate(() => {
        const s = document.createElement('script')
        s.textContent = 'window.__injected = 1'
        document.body.append(s)
        return (window as { __injected?: number }).__injected
      }),
    ).toBeUndefined()

    // Drag a region.
    await page.mouse.move(120, 100)
    await page.mouse.down()
    await page.mouse.move(520, 360, { steps: 5 })
    await page.mouse.up()

    // The capture reaches the server once, as a PNG of the region (any display scale).
    await expect.poll(() => received.length).toBe(1)
    const png = received[0].image
    expect(png.subarray(1, 4).toString()).toBe('PNG')
    const width = png.readUInt32BE(16)
    const height = png.readUInt32BE(20)
    expect(width / height).toBeCloseTo(400 / 260, 1)
    expect(received[0].voice).toBe('en-US-AriaNeural')

    // The lesson plays over the region, with the demo notice and Scribbly.
    const board = page.locator('svg.board')
    await expect(board).toHaveAttribute('data-status', 'running')
    await expect(page.getByTestId('demo')).toContainText('Demo lesson')
    await expect(page.locator('.overlay-board')).toHaveCSS('left', '40px')
    await expect(page.locator('.overlay-board')).toHaveCSS('width', '560px') // grown to the minimum
    await expect(page.locator('[data-motion]')).toBeVisible()
    await expect(page.locator('.sub-en')).toContainText('point charge')
    await expect(page.locator('.step-list')).toHaveCount(0)

    // Esc: Scribbly leaves, then the window closes; the app keeps running in the tray.
    const closed = page.waitForEvent('close')
    await page.keyboard.press('Escape')
    await closed
    expect(await test.call('overlayActive')).toBe(false)
    expect(await test.call('hasTray')).toBe(true)
  } finally {
    await app.close()
    server.close()
  }
})
