import { describe, expect, it } from 'vitest'
import { CANVAS } from '../board/geometry'
import {
  boardPlacement,
  boardToWindow,
  cropRect,
  dockRect,
  dragRect,
  fitWithin,
  MIN_BOARD,
  nearestCorner,
  sanitizeRegion,
  type Rect,
  type Size,
} from './geometry'

const FULL_VIEW: Rect = { x: 0, y: 0, w: CANVAS.w, h: CANVAS.h }

/** A 1920×1080 panel at a Windows display scale: its DIP size and its capture size. */
function panel(scale: number): { dip: Size; image: Size } {
  return { dip: { w: 1920 / scale, h: 1080 / scale }, image: { w: 1920, h: 1080 } }
}

describe('cropRect: selected DIP region → capture pixels', () => {
  it.each([
    [1, { x: 100, y: 50, w: 400, h: 200 }],
    [1.25, { x: 125, y: 62, w: 500, h: 251 }],
    [1.5, { x: 150, y: 75, w: 600, h: 300 }],
  ])('maps at %s× scale', (scale, expected) => {
    const { dip, image } = panel(scale)
    expect(cropRect({ x: 100, y: 50, w: 400, h: 200 }, dip, image)).toEqual(expected)
  })

  it('rounds outwards so fractional pixels at 125 % are never cut off', () => {
    const { dip, image } = panel(1.25)
    const crop = cropRect({ x: 101, y: 33, w: 99, h: 41 }, dip, image)
    expect(crop.x).toBeLessThanOrEqual(101 * 1.25)
    expect(crop.y).toBeLessThanOrEqual(33 * 1.25)
    expect(crop.x + crop.w).toBeGreaterThanOrEqual(200 * 1.25)
    expect(crop.y + crop.h).toBeGreaterThanOrEqual(74 * 1.25)
  })

  it('uses the real capture size, not the nominal scale factor', () => {
    // A 4K panel at 150 % whose capture came back downscaled to 1920×1080.
    const crop = cropRect(
      { x: 0, y: 0, w: 1280, h: 720 },
      { w: 2560, h: 1440 },
      { w: 1920, h: 1080 },
    )
    expect(crop).toEqual({ x: 0, y: 0, w: 960, h: 540 })
  })

  it('stays inside the image at the display edges', () => {
    const { dip, image } = panel(1.5)
    expect(cropRect({ x: 1200, y: 700, w: 80, h: 20 }, dip, image)).toEqual({
      x: 1800,
      y: 1050,
      w: 120,
      h: 30,
    })
  })
})

describe('boardPlacement: where the board is drawn', () => {
  const display: Size = { w: 1536, h: 864 } // 1920×1080 at 125 %

  it('covers a large region exactly', () => {
    const region = { x: 200, y: 100, w: 800, h: 500 }
    expect(boardPlacement(region, display)).toEqual(region)
  })

  it('grows a small region around its centre to the minimum size', () => {
    const p = boardPlacement({ x: 700, y: 400, w: 100, h: 40 }, display)
    expect(p).toEqual({ x: 750 - MIN_BOARD.w / 2, y: 420 - MIN_BOARD.h / 2, ...MIN_BOARD })
  })

  it('keeps a grown board on screen near an edge', () => {
    const p = boardPlacement({ x: 1500, y: 840, w: 30, h: 24 }, display)
    expect(p.x + p.w).toBe(display.w)
    expect(p.y + p.h).toBe(display.h)
  })

  it('never exceeds a small display', () => {
    const p = boardPlacement({ x: 0, y: 0, w: 100, h: 100 }, { w: 400, h: 300 })
    expect(p).toEqual({ x: 0, y: 0, w: 400, h: 300 })
  })
})

describe('boardToWindow: board coordinates → overlay window DIP', () => {
  it('fits the 1600×1000 board into the placement (meet) and centres it', () => {
    const placement = { x: 100, y: 100, w: 800, h: 800 } // taller than 16:10
    expect(boardToWindow([0, 0], FULL_VIEW, placement)).toEqual([100, 250])
    expect(boardToWindow([1600, 1000], FULL_VIEW, placement)).toEqual([900, 750])
  })

  it('follows the per-step zoom of the view box', () => {
    const view = { x: 400, y: 250, w: 800, h: 500 }
    const placement = { x: 0, y: 0, w: 1600, h: 1000 }
    expect(boardToWindow([400, 250], view, placement)).toEqual([0, 0])
    expect(boardToWindow([800, 500], view, placement)).toEqual([800, 500])
  })

  it.each([1, 1.25, 1.5])(
    'lands a board point on the same captured pixel at %s× (second monitor)',
    (scale) => {
      // Window DIP are relative to the display, so a monitor's position does not matter.
      const { dip, image } = panel(scale)
      const region = { x: 200, y: 100, w: 640, h: 400 }
      const placement = boardPlacement(region, dip)
      const crop = cropRect(region, dip, image)

      const centre = boardToWindow([800, 500], FULL_VIEW, placement)
      const pixel = cropRect({ x: centre[0], y: centre[1], w: 0, h: 0 }, dip, image)
      // The board centre is the centre of the captured region, in physical pixels too.
      expect(pixel.x).toBeCloseTo(crop.x + crop.w / 2, 0)
      expect(pixel.y).toBeCloseTo(crop.y + crop.h / 2, 0)

      const corner = boardToWindow([1600, 1000], FULL_VIEW, placement)
      expect(corner[0]).toBeLessThanOrEqual(region.x + region.w + 1e-9)
      expect(corner[1]).toBeLessThanOrEqual(region.y + region.h + 1e-9)
    },
  )
})

describe('selection helpers', () => {
  const display = { w: 1280, h: 720 }

  it('normalizes a drag in any direction and clips it to the display', () => {
    expect(dragRect([500, 400], [100, -50], display)).toEqual({ x: 100, y: 0, w: 400, h: 400 })
    expect(dragRect([1200, 700], [1400, 900], display)).toEqual({ x: 1200, y: 700, w: 80, h: 20 })
  })

  it('accepts only finite, usable regions from the page', () => {
    expect(sanitizeRegion({ x: 10, y: 10, w: 100, h: 50 }, display)).toEqual({
      x: 10,
      y: 10,
      w: 100,
      h: 50,
    })
    expect(sanitizeRegion({ x: 10, y: 10, w: 5, h: 50 }, display)).toBeNull()
    expect(sanitizeRegion({ x: NaN, y: 10, w: 100, h: 50 }, display)).toBeNull()
    expect(sanitizeRegion({ x: '1', y: 10, w: 100, h: 50 }, display)).toBeNull()
    expect(sanitizeRegion(null, display)).toBeNull()
    expect(sanitizeRegion({ x: 5000, y: 10, w: 100, h: 50 }, display)).toBeNull()
  })

  it('downscales a large capture to the upload limit, keeping the aspect ratio', () => {
    expect(fitWithin({ w: 3200, h: 1800 }, 1600)).toEqual({ w: 1600, h: 900 })
    expect(fitWithin({ w: 300, h: 200 }, 1600)).toEqual({ w: 300, h: 200 })
  })

  it('pops Scribbly in from the corner nearest the board', () => {
    const [x1, y1] = nearestCorner({ x: 900, y: 500, w: 200, h: 100 }, display)
    expect(x1).toBeGreaterThan(display.w / 2)
    expect(y1).toBeGreaterThan(display.h / 2)
    const [x2, y2] = nearestCorner({ x: 50, y: 50, w: 200, h: 100 }, display)
    expect(x2).toBeLessThan(display.w / 2)
    expect(y2).toBeLessThan(display.h / 2)
  })

  it('docks subtitles below the board, or above it when there is no room', () => {
    const below = dockRect({ x: 100, y: 100, w: 600, h: 300 }, display, 150)
    expect(below.y).toBe(410)
    const above = dockRect({ x: 100, y: 400, w: 600, h: 300 }, display, 150)
    expect(above.y).toBe(240)
    const inside = dockRect({ x: 0, y: 0, w: 1280, h: 720 }, display, 150)
    expect(inside.y + inside.h).toBeLessThanOrEqual(720)
  })
})
