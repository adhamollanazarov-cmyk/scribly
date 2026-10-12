import { expect, test } from '@playwright/test'
import { readFileSync } from 'node:fs'

const events = JSON.parse(
  readFileSync(new URL('../../shared/streams/gauss_law.json', import.meta.url), 'utf-8'),
) as { event: string; data: object }[]

test('a cleanly closed incomplete stream shows an error instead of waiting forever', async ({
  page,
}) => {
  const meta = events[0]
  await page.route('**/lessons', (route) =>
    route.fulfill({
      contentType: 'text/event-stream',
      body: `event: meta\ndata: ${JSON.stringify(meta.data)}\n\n`,
    }),
  )
  await page.route('**/audio/**', (route) => route.abort())
  await page.goto('/')
  await page.getByRole('button', { name: "Gauss's law" }).click()
  await expect(page.locator('svg.board')).toHaveAttribute('data-status', 'error')
  await expect(page.locator('.sub-error')).toContainText('Cannot reach the Scribbly server')
  await expect(page.locator('.step-list .placeholder')).toHaveCount(0)
})
