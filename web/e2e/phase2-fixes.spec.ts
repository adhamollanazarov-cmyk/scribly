import { expect, test, type Page } from '@playwright/test'
import { readFileSync } from 'node:fs'

interface Event {
  event: string
  data: {
    id?: string
    checkpoint?: { answer: number; type: 'number' | 'choice' } | null
    audio_url?: string | null
    [key: string]: unknown
  }
}

function stream(name: string): Event[] {
  return JSON.parse(
    readFileSync(new URL(`../../shared/streams/${name}.json`, import.meta.url), 'utf-8'),
  )
}

// Generated in memory; no provider calls or saved audio/captures.
function silentWav(seconds: number): Buffer {
  const rate = 8000
  const samples = Math.round(seconds * rate)
  const wav = Buffer.alloc(44 + samples, 128)
  wav.write('RIFF', 0)
  wav.writeUInt32LE(36 + samples, 4)
  wav.write('WAVEfmt ', 8)
  wav.writeUInt32LE(16, 16)
  wav.writeUInt16LE(1, 20)
  wav.writeUInt16LE(1, 22)
  wav.writeUInt32LE(rate, 24)
  wav.writeUInt32LE(rate, 28)
  wav.writeUInt16LE(1, 32)
  wav.writeUInt16LE(8, 34)
  wav.write('data', 36)
  wav.writeUInt32LE(samples, 40)
  return wav
}

async function mock(page: Page, events: Event[], seconds = 0.8) {
  const body = events.map((e) => `event: ${e.event}\ndata: ${JSON.stringify(e.data)}\n\n`).join('')
  await page.route('**/lessons', (route) =>
    route.fulfill({ status: 200, contentType: 'text/event-stream', body }),
  )
  await page.route('**/audio/*.mp3', (route) =>
    route.fulfill({ status: 200, contentType: 'audio/wav', body: silentWav(seconds) }),
  )
}

test('series equations and legends fit the board without overlapping, with measured highlights', async ({
  page,
}) => {
  const events = stream('circ_series')
  await mock(page, events)
  await page.goto('/')
  await page.getByRole('slider').fill('1.5')
  await page.getByRole('button', { name: 'Series circuit' }).click()
  const board = page.locator('svg.board')
  for (const e of events.filter((e) => e.event === 'step' && e.data.checkpoint)) {
    await expect(board).toHaveAttribute('data-stage', 'answer', { timeout: 30_000 })
    await expect(board).toHaveAttribute('data-step', e.data.id!)
    if (e.data.checkpoint!.type === 'choice') {
      await page.locator('.checkpoint .choice').nth(e.data.checkpoint!.answer).click()
    } else {
      await page.getByLabel('Your answer').fill(String(e.data.checkpoint!.answer))
      await page.getByRole('button', { name: 'Check', exact: true }).click()
    }
    await expect(page.getByText('Correct!', { exact: true })).toBeVisible()
    await page.getByRole('button', { name: 'Continue', exact: true }).click()
  }
  await expect(board).toHaveAttribute('data-status', 'finished', { timeout: 30_000 })
  await page.evaluate(() => document.fonts.ready)
  const boxes = await board.locator('[data-bounds] foreignObject > div').evaluateAll((els) => {
    const svg = document.querySelector<SVGSVGElement>('svg.board')!
    const origin = svg.getBoundingClientRect()
    const scale = svg.getScreenCTM()!.a
    return els.map((el) => {
      const group = el.closest('[data-prim]')!
      const b = JSON.parse(group.getAttribute('data-bounds')!)
      const r = el.getBoundingClientRect()
      return {
        id: group.getAttribute('data-prim'),
        measured: b,
        actual: {
          x: (r.x - origin.x) / scale,
          y: (r.y - origin.y) / scale,
          w: r.width / scale,
          h: r.height / scale,
        },
      }
    })
  })
  expect(boxes.length).toBeGreaterThan(12)
  for (const { id, measured: b, actual: a } of boxes) {
    for (const key of ['x', 'y', 'w', 'h'] as const) {
      expect(Math.abs(b[key] - a[key]), `${id} measured ${key}`).toBeLessThan(1.5)
    }
    expect(a.x, `${id} left`).toBeGreaterThanOrEqual(0)
    expect(a.y, `${id} top`).toBeGreaterThanOrEqual(0)
    expect(a.x + a.w, `${id} right`).toBeLessThanOrEqual(1600)
    expect(a.y + a.h, `${id} bottom`).toBeLessThanOrEqual(1000)
  }
  for (let i = 0; i < boxes.length; i++) {
    for (let j = i + 1; j < boxes.length; j++) {
      const a = boxes[i].actual
      const b = boxes[j].actual
      const overlap = a.x < b.x + b.w && b.x < a.x + a.w && a.y < b.y + b.h && b.y < a.y + a.h
      expect(overlap, `${boxes[i].id} overlaps ${boxes[j].id}`).toBe(false)
    }
  }
  const target = boxes.find((b) => b.id === 'i-eq')!.actual
  const loop = await board.locator('[data-prim="i-hl"] path').evaluate((p) => {
    const b = (p as SVGGraphicsElement).getBBox()
    return { x: b.x, y: b.y, w: b.width, h: b.height }
  })
  expect(loop.x).toBeLessThan(target.x)
  expect(loop.x + loop.w).toBeGreaterThan(target.x + target.w)
  expect(loop.w).toBeLessThan(target.w + 75)
})

test('handwriting uses loaded font advances and renders the superscript minus', async ({
  page,
}) => {
  const events = stream('plot_square')
  const step = events.find((e) => e.event === 'step')!
  step.data.draw = [
    { id: 'measured', type: 'text', x: 100, y: 200, text: '10⁻⁹ iiiWWW', size: 40, at: 0 },
  ]
  step.data.say = 'Read the exponent and the label.'
  step.data.duration_s = 5
  await mock(page, [events[0], step, events.at(-1)!], 5)
  await page.goto('/')
  await page.getByRole('button', { name: "Gauss's law" }).click()
  const label = page.locator('[data-prim="measured"] text')
  await expect(label.locator('tspan[baseline-shift="super"]')).toHaveText('-9')
  // Pause only once the label is fully drawn: pausing mid-stroke leaves the pen (and the
  // mascot) part-way along the text, which made this test depend on page-load speed.
  await expect(page.locator('[data-prim="measured"]')).toHaveAttribute('data-drawn', 'true')
  await page.getByRole('button', { name: /Pause/ }).click()
  await page.evaluate(() => document.fonts.ready)
  const result = await label.evaluate((el) => {
    const text = el as SVGTextElement
    const bounds = JSON.parse(el.closest('[data-bounds]')!.getAttribute('data-bounds')!)
    return {
      text: text.textContent,
      actual: text.getComputedTextLength(),
      advance: bounds.advances[text.getNumberOfChars()],
    }
  })
  expect(result.text).not.toContain('⁻')
  expect(Math.abs(result.actual - result.advance)).toBeLessThan(1)
  // The mascot's anchor is the current pen position (its body/pencil use local offsets).
  await expect
    .poll(async () => {
      const penX = await page
        .getByTestId('mascot')
        .evaluate((el) => new DOMMatrix(getComputedStyle(el).transform).e)
      return Math.abs(penX - (100 + result.actual))
    })
    .toBeLessThan(1.5)
})

test('a server-sampled bare plot and its referenced highlight play end to end', async ({
  page,
}) => {
  await mock(page, stream('plot_square'))
  await page.goto('/')
  await page.getByRole('slider').fill('1.5')
  await page.getByRole('button', { name: "Gauss's law" }).click()
  const board = page.locator('svg.board')
  await expect(board).toHaveAttribute('data-status', 'finished', { timeout: 20_000 })
  await expect(board.locator('[data-prim="square"][data-type="curve"] path')).toBeVisible()
  await expect(board.locator('[data-type="plot"]')).toHaveCount(0)
  await expect(board.locator('[data-type="highlight"] path')).toBeVisible()
  const box = await board.locator('[data-prim="square"] path').evaluate((p) => {
    const b = (p as SVGGraphicsElement).getBBox()
    return [b.x, b.y, b.width, b.height]
  })
  expect(box.every(Number.isFinite)).toBe(true)
  expect(box[2]).toBeGreaterThan(790)
  expect(box[3]).toBeGreaterThan(490)
})

test('keyboard focus on the topic/problem choice is visible on its label', async ({ page }) => {
  await page.goto('/')
  const label = (name: string) =>
    page.locator('.segmented label', { has: page.getByRole('radio', { name }) })
  const outline = (name: string) => label(name).evaluate((el) => getComputedStyle(el).outlineStyle)

  await expect(page.getByRole('radio', { name: 'Topic' })).toBeChecked()
  await page.locator('#lesson-text').focus()
  await page.keyboard.press('Shift+Tab')
  await expect(page.getByRole('radio', { name: 'Topic' })).toBeFocused()
  expect(await outline('Topic')).toBe('solid')

  await page.keyboard.press('ArrowRight')
  await expect(page.getByRole('radio', { name: 'Problem' })).toBeChecked()
  expect(await outline('Problem')).toBe('solid')
  expect(await outline('Topic')).toBe('none')
})
