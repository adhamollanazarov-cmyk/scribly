// The overlay page's only link to Electron: `window.scribbly`, set by desktop's preload.
// desktop/src/preload implements this contract; keep the two in step.

import type { Rect } from './geometry'
import type { OverlaySettings } from './settings'

export interface LessonMode {
  mode: 'lesson'
  /** The selected region in window DIP. */
  region: Rect
  /** The captured region (PNG). Kept in memory only, sent once to the server. */
  imagePngBase64: string
  settings: OverlaySettings
  /** True when another app holds Esc, so Esc cannot close the lesson. */
  escapeTaken?: boolean
}

export type OverlayMode = { mode: 'select' } | LessonMode | { mode: 'dismiss' }

export interface OverlayBridge {
  /** Main → page: what to show. Returns an unsubscribe function. */
  onMode(listener: (mode: OverlayMode) => void): () => void
  /** The dragged region, or null when the user cancelled. */
  selectRegion(region: Rect | null): void
  /** True while the pointer is over Scribbly, the pill or a card; clicks pass through otherwise. */
  setInteractive(interactive: boolean): void
  /** Scribbly has left; close the overlay window. */
  closeLesson(): void
}

/** A 1×1 transparent PNG: stands in for a screenshot outside Electron. */
const BLANK_PNG =
  'iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNkYAAAAAYAAjCB0C8AAAAASUVORK5CYII='

/**
 * For `npm run dev` in a normal browser (mock mode UI work): `overlay.html` starts a demo
 * lesson over the middle of the page; `overlay.html?select` starts with the selector.
 */
export function devBridge(settings: OverlaySettings, win: Window = window): OverlayBridge {
  let listener: ((mode: OverlayMode) => void) | null = null
  const lesson = (region: Rect): LessonMode => ({
    mode: 'lesson',
    region,
    imagePngBase64: BLANK_PNG,
    settings,
  })
  const middle = (): Rect => {
    const w = win.innerWidth * 0.6
    const h = win.innerHeight * 0.6
    return { x: (win.innerWidth - w) / 2, y: (win.innerHeight - h) / 2, w, h }
  }
  return {
    onMode(next) {
      listener = next
      const start = win.location.search.includes('select') ? { mode: 'select' as const } : null
      queueMicrotask(() => listener?.(start ?? lesson(middle())))
      return () => {
        listener = null
      }
    },
    selectRegion(region) {
      listener?.(region ? lesson(region) : { mode: 'select' })
    },
    setInteractive() {},
    closeLesson() {
      listener?.({ mode: 'select' })
    },
  }
}

declare global {
  interface Window {
    scribbly?: OverlayBridge
  }
}
