import { desktopCapturer, type Display } from 'electron'
import { cropRect, fitWithin, type Rect } from '../../../web/src/overlay/geometry'

/** Longest side of the image sent to the server (vision models downscale beyond this). */
export const MAX_UPLOAD_SIDE = 1600

/** The capture source for a display: by display id, else by position in the display list. */
export function pickSource<T extends { display_id: string }>(
  sources: readonly T[],
  displayId: number,
  displayIndex: number,
): T | null {
  const byId = sources.find((s) => s.display_id === String(displayId))
  if (byId) return byId
  if (sources.every((s) => !s.display_id)) return sources[displayIndex] ?? null
  return null
}

/**
 * Captures one display and returns only the selected region as base64 PNG. The full screen
 * image is dropped right away; nothing is written to disk.
 */
export async function captureRegion(
  display: Display,
  displayIndex: number,
  region: Rect,
): Promise<string> {
  const { width, height } = display.bounds
  const thumbnailSize = {
    width: Math.round(width * display.scaleFactor),
    height: Math.round(height * display.scaleFactor),
  }
  const sources = await desktopCapturer.getSources({ types: ['screen'], thumbnailSize })
  const source = pickSource(sources, display.id, displayIndex)
  if (!source || source.thumbnail.isEmpty()) throw new Error('no capture for this display')
  const full = source.thumbnail.getSize()
  const crop = cropRect(region, { w: width, h: height }, { w: full.width, h: full.height })
  if (crop.w < 1 || crop.h < 1) throw new Error('empty capture region')
  let image = source.thumbnail.crop({ x: crop.x, y: crop.y, width: crop.w, height: crop.h })
  const fit = fitWithin(crop, MAX_UPLOAD_SIDE)
  if (fit.w !== crop.w) image = image.resize({ width: fit.w, height: fit.h, quality: 'good' })
  return image.toPNG().toString('base64')
}
