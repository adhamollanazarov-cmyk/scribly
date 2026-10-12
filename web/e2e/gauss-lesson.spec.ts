// AGENTS.md §8: the golden Gauss lesson plays end to end in mock mode, audio and drawing in
// sync. The SSE body is exactly what the server sends with MOCK_AI=1 (shared/streams, kept
// current by a server test); audio is real, silent WAV, so the browser loads, plays and ends it.

import { expect, test, type Page } from '@playwright/test'
import { readFileSync } from 'node:fs'

interface Event {
  event: string
  data: { id: string; audio_url?: string | null; checkpoint?: { answer: number } | null }
}

const events: Event[] = JSON.parse(
  readFileSync(new URL('../../shared/streams/gauss_law.json', import.meta.url), 'utf-8'),
)
const steps = events.filter((e) => e.event === 'step').map((e) => e.data)
const AUDIO_SECONDS = 1.6

/** Mono 8-bit PCM silence. */
function silentWav(seconds: number): Buffer {
  const rate = 8000
  const samples = Math.round(seconds * rate)
  const wav = Buffer.alloc(44 + samples, 128)
  wav.write('RIFF', 0)
  wav.writeUInt32LE(36 + samples, 4)
  wav.write('WAVEfmt ', 8)
  wav.writeUInt32LE(16, 16)
  wav.writeUInt16LE(1, 20) // PCM
  wav.writeUInt16LE(1, 22) // mono
  wav.writeUInt32LE(rate, 24)
  wav.writeUInt32LE(rate, 28)
  wav.writeUInt16LE(1, 32)
  wav.writeUInt16LE(8, 34)
  wav.write('data', 36)
  wav.writeUInt32LE(samples, 40)
  return wav
}

async function mockServer(page: Page) {
  const audioRequests = new Set<string>()
  const body = events.map((e) => `event: ${e.event}\ndata: ${JSON.stringify(e.data)}\n\n`).join('')
  await page.route('**/lessons', (route) =>
    route.fulfill({ status: 200, contentType: 'text/event-stream', body }),
  )
  await page.route('**/audio/*.mp3', (route) => {
    audioRequests.add(new URL(route.request().url()).pathname)
    return route.fulfill({ status: 200, contentType: 'audio/wav', body: silentWav(AUDIO_SECONDS) })
  })
  return audioRequests
}

test('the Gauss lesson plays every step with audio and drawing, without errors', async ({
  page,
}) => {
  test.setTimeout(90_000)
  const errors: string[] = []
  page.on('console', (msg) => {
    if (msg.type() === 'error') errors.push(msg.text())
  })
  page.on('pageerror', (err) => errors.push(err.message))
  const audioRequests = await mockServer(page)

  await page.goto('/')
  await page.getByRole('slider').fill('1.5')
  await page.getByRole('button', { name: "Gauss's law" }).click()

  const board = page.locator('svg.board')
  await expect(board).toHaveAttribute('data-step', 's1')
  await expect(page.locator('.sub-en')).toContainText('positive point charge')

  const checkpoint = steps.find((s) => s.checkpoint)!
  await expect(board).toHaveAttribute('data-stage', 'answer', { timeout: 30_000 })
  await expect(board).toHaveAttribute('data-step', checkpoint.id)
  await expect(page.getByTestId('mascot')).toHaveAttribute('data-state', 'listening')
  await page.locator('.checkpoint .choice').nth(checkpoint.checkpoint!.answer).click()
  await expect(page.getByText('Correct!')).toBeVisible()
  await expect(page.getByTestId('mascot')).toHaveAttribute('data-state', 'happy')
  await page.getByRole('button', { name: 'Continue' }).click()

  await expect(board).toHaveAttribute('data-status', 'finished', { timeout: 30_000 })
  for (const step of steps) {
    const item = page.locator(`.step-list li[data-step-id="${step.id}"]`)
    await expect(item, `step ${step.id}`).toHaveAttribute('data-audio', 'ended')
    await expect(item, `step ${step.id}`).toHaveAttribute('data-drawn', 'true')
    expect(audioRequests).toContain(step.audio_url)
  }
  const prims = board.locator('.board-lesson [data-prim]')
  expect(await prims.count()).toBeGreaterThan(20)
  await expect(board.locator('.board-lesson [data-drawn="false"]')).toHaveCount(0)
  await expect(board.locator('.katex').first()).toBeVisible()
  await expect(page.getByTestId('mascot')).toHaveAttribute('data-state', 'idle')
  expect(errors).toEqual([])
})

test('a step can be replayed from the step list', async ({ page }) => {
  await mockServer(page)
  await page.goto('/')
  await page.getByRole('slider').fill('1.5')
  await page.getByRole('button', { name: "Gauss's law" }).click()
  const board = page.locator('svg.board')
  await expect(board).toHaveAttribute('data-step', 's3', { timeout: 20_000 })

  await page.locator('.step-list li[data-step-id="s1"] button').click()
  await expect(board).toHaveAttribute('data-step', 's1')
  // Later steps' drawings leave the board when we go back.
  await expect(board.locator('[data-prim="surface1-sphere"]')).toHaveCount(0)
})
