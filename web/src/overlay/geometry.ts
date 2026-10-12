// Pure geometry for the desktop overlay. Used by the overlay page and by Electron's main
// process (desktop/ bundles this file), so it has no imports from the DOM or Node.
//
// Coordinate spaces:
// - DIP: device-independent pixels relative to one display's top-left. The selector and the
//   lesson overlay windows cover exactly one display, so their CSS pixels are DIPs.
// - Image pixels: the physical pixels of a screen capture (DIP × the display's scale factor).
// - Board: the lesson's virtual 1600×1000 canvas, shown through a zooming view box.

export type Point = readonly [number, number]

export interface Rect {
  x: number
  y: number
  w: number
  h: number
}

export interface Size {
  w: number
  h: number
}

/** Smallest region the selector accepts, in DIP. */
export const MIN_REGION = 24
/** The board is grown to at least this size so a lesson over a small region stays readable. */
export const MIN_BOARD: Size = { w: 560, h: 350 }

const clamp = (v: number, lo: number, hi: number) => Math.min(hi, Math.max(lo, v))

/** The rectangle spanned by a drag from `a` to `b`, clipped to the display. */
export function dragRect(a: Point, b: Point, display: Size): Rect {
  const x1 = clamp(Math.min(a[0], b[0]), 0, display.w)
  const y1 = clamp(Math.min(a[1], b[1]), 0, display.h)
  const x2 = clamp(Math.max(a[0], b[0]), 0, display.w)
  const y2 = clamp(Math.max(a[1], b[1]), 0, display.h)
  return { x: x1, y: y1, w: x2 - x1, h: y2 - y1 }
}

export function isUsableRegion(r: Rect): boolean {
  return r.w >= MIN_REGION && r.h >= MIN_REGION
}

/** A finite rectangle inside the display with a usable size, or null. */
export function sanitizeRegion(value: unknown, display: Size): Rect | null {
  if (typeof value !== 'object' || value === null) return null
  const { x, y, w, h } = value as Record<string, unknown>
  const nums = [x, y, w, h]
  if (!nums.every((n) => typeof n === 'number' && Number.isFinite(n))) return null
  const r = dragRect(
    [x as number, y as number],
    [(x as number) + (w as number), (y as number) + (h as number)],
    display,
  )
  return isUsableRegion(r) ? r : null
}

/**
 * The capture pixels under a DIP region. `image` is the real capture size, so this works
 * for any Windows scale factor (100/125/150 %…) without trusting the factor itself.
 * Rounds outwards so the crop always covers the whole region.
 */
export function cropRect(region: Rect, display: Size, image: Size): Rect {
  const sx = image.w / display.w
  const sy = image.h / display.h
  const x1 = clamp(Math.floor(region.x * sx + 1e-9), 0, image.w)
  const y1 = clamp(Math.floor(region.y * sy + 1e-9), 0, image.h)
  const x2 = clamp(Math.ceil((region.x + region.w) * sx - 1e-9), 0, image.w)
  const y2 = clamp(Math.ceil((region.y + region.h) * sy - 1e-9), 0, image.h)
  return { x: x1, y: y1, w: x2 - x1, h: y2 - y1 }
}

/** Fit `size` inside `max` keeping its aspect ratio (never enlarges). */
export function fitWithin(size: Size, max: number): Size {
  const k = Math.min(1, max / Math.max(size.w, size.h))
  return { w: Math.max(1, Math.round(size.w * k)), h: Math.max(1, Math.round(size.h * k)) }
}

/**
 * Where the board goes in the overlay window: exactly over the selected region, or grown
 * around its centre to `MIN_BOARD` (and kept on screen) when the region is small.
 */
export function boardPlacement(region: Rect, display: Size, min: Size = MIN_BOARD): Rect {
  const w = Math.min(display.w, Math.max(region.w, min.w))
  const h = Math.min(display.h, Math.max(region.h, min.h))
  const cx = region.x + region.w / 2
  const cy = region.y + region.h / 2
  return {
    x: clamp(cx - w / 2, 0, display.w - w),
    y: clamp(cy - h / 2, 0, display.h - h),
    w,
    h,
  }
}

/** Scale and offset of a view box drawn into `placement` with preserveAspectRatio "meet". */
export function viewTransform(view: Rect, placement: Rect): { k: number; x: number; y: number } {
  const k = Math.min(placement.w / view.w, placement.h / view.h)
  return {
    k,
    x: placement.x + (placement.w - view.w * k) / 2 - view.x * k,
    y: placement.y + (placement.h - view.h * k) / 2 - view.y * k,
  }
}

/** A board point in overlay-window DIP. */
export function boardToWindow(point: Point, view: Rect, placement: Rect): [number, number] {
  const t = viewTransform(view, placement)
  return [t.x + point[0] * t.k, t.y + point[1] * t.k]
}

/** Scribbly pops in from the screen corner nearest the board (pencil-tip position). */
export function nearestCorner(target: Rect, display: Size, inset = 60): [number, number] {
  const left = target.x + target.w / 2 < display.w / 2
  const top = target.y + target.h / 2 < display.h / 2
  // The body is drawn up and to the right of the pencil tip.
  return [left ? inset : display.w - inset * 2.5, top ? inset * 2.5 : display.h - inset]
}

/** Where the subtitles + pill dock goes: below the board, else above it, else inside it. */
export function dockRect(placement: Rect, display: Size, height: number, gap = 10): Rect {
  const w = Math.min(display.w - 2 * gap, Math.max(placement.w, 420))
  const x = clamp(placement.x + (placement.w - w) / 2, gap, display.w - gap - w)
  const below = placement.y + placement.h + gap
  if (below + height <= display.h - gap) return { x, y: below, w, h: height }
  const above = placement.y - gap - height
  if (above >= gap) return { x, y: above, w, h: height }
  return { x, y: placement.y + placement.h - height - gap, w, h: height }
}

export function distance(a: Point, b: Point): number {
  return Math.hypot(b[0] - a[0], b[1] - a[1])
}
