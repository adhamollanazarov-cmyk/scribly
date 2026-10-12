// One hotkey press: a dimmed selector on every display → the user drags a region → that
// region is captured → the selector window on that display turns into the click-through
// lesson overlay. Esc cancels the selection or lets Scribbly leave and closes the lesson.
import { BrowserWindow, globalShortcut, screen, type Display, type WebContents } from 'electron'
import { t } from '../../../web/src/i18n'
import type { OverlayMode } from '../../../web/src/overlay/bridge'
import { sanitizeRegion } from '../../../web/src/overlay/geometry'
import type { OverlaySettings } from '../../../web/src/overlay/settings'
import { CHANNEL } from '../shared/channels'
import { captureRegion } from './capture'
import { createOverlayWindow } from './windows'

/** Time for Windows to repaint without our dimmed windows before the capture. */
const CAPTURE_SETTLE_MS = 150
/** If the page never reports that Scribbly left, close anyway. */
const DISMISS_FALLBACK_MS = 1500

interface Shown {
  win: BrowserWindow
  display: Display
  index: number
}

export interface OverlayDeps {
  preload: string
  devTools: boolean
  load: (win: BrowserWindow) => Promise<void>
  settings: () => OverlaySettings
  notify: (message: string) => void
}

const delay = (ms: number) => new Promise((done) => setTimeout(done, ms))

export class OverlayController {
  private selectors = new Map<number, Shown>() // by webContents id
  private lesson: (Shown & { id: number }) | null = null
  private dismissTimer: ReturnType<typeof setTimeout> | null = null
  private deps: OverlayDeps

  constructor(deps: OverlayDeps) {
    this.deps = deps
  }

  /** IPC is accepted only from our own overlay windows. */
  owns(sender: WebContents): boolean {
    return this.selectors.has(sender.id) || this.lesson?.id === sender.id
  }

  get active(): boolean {
    return this.selectors.size > 0 || this.lesson !== null
  }

  startSelection(): void {
    this.closeAll()
    const cursor = screen.getDisplayNearestPoint(screen.getCursorScreenPoint())
    screen.getAllDisplays().forEach((display, index) => {
      const win = createOverlayWindow(display, this.deps.preload, this.deps.devTools)
      const id = win.webContents.id
      this.selectors.set(id, { win, display, index })
      win.on('closed', () => this.forget(id))
      win.webContents.once('did-finish-load', () => send(win, { mode: 'select' }))
      win.once('ready-to-show', () => {
        win.show()
        if (display.id === cursor.id) win.focus()
      })
      void this.deps.load(win)
    })
    this.registerEscape()
  }

  async select(sender: WebContents, raw: unknown): Promise<void> {
    const shown = this.selectors.get(sender.id)
    if (!shown) return
    const { win, display, index } = shown
    const size = { w: display.bounds.width, h: display.bounds.height }
    const region = raw === null ? null : sanitizeRegion(raw, size)
    if (!region) return this.closeAll()

    for (const s of this.selectors.values()) s.win.setOpacity(0)
    await delay(CAPTURE_SETTLE_MS)
    let image: string
    try {
      image = await captureRegion(display, index, region)
    } catch (error) {
      console.error('Capture failed:', error instanceof Error ? error.message : 'unknown')
      this.closeAll()
      this.deps.notify(t('tray.captureFailed'))
      return
    }
    if (win.isDestroyed()) return

    for (const s of this.selectors.values()) if (s.win !== win) s.win.destroy()
    this.selectors.clear()
    this.lesson = { ...shown, id: sender.id }
    win.setIgnoreMouseEvents(true, { forward: true })
    send(win, { mode: 'lesson', region, imagePngBase64: image, settings: this.deps.settings() })
    win.setOpacity(1)
  }

  setInteractive(sender: WebContents, interactive: boolean): void {
    if (this.lesson?.id !== sender.id) return
    this.lesson.win.setIgnoreMouseEvents(!interactive, { forward: true })
  }

  closeLesson(sender: WebContents): void {
    if (this.lesson?.id === sender.id) this.closeAll()
  }

  /** Esc: cancel the selection, or let Scribbly leave and then close. */
  escape(): void {
    if (this.selectors.size) return this.closeAll()
    if (!this.lesson || this.dismissTimer) return
    send(this.lesson.win, { mode: 'dismiss' })
    this.dismissTimer = setTimeout(() => this.closeAll(), DISMISS_FALLBACK_MS)
  }

  closeAll(): void {
    if (this.dismissTimer) clearTimeout(this.dismissTimer)
    this.dismissTimer = null
    const windows = [...this.selectors.values()].map((s) => s.win)
    if (this.lesson) windows.push(this.lesson.win)
    this.selectors.clear()
    this.lesson = null
    for (const win of windows) if (!win.isDestroyed()) win.destroy()
    this.unregisterEscape()
  }

  private forget(id: number): void {
    this.selectors.delete(id)
    if (this.lesson?.id === id) this.lesson = null
    if (!this.active) this.closeAll()
  }

  // Esc is global only while an overlay is open, so other apps keep it the rest of the time.
  private registerEscape(): void {
    if (!globalShortcut.isRegistered('Escape'))
      globalShortcut.register('Escape', () => this.escape())
  }

  private unregisterEscape(): void {
    if (globalShortcut.isRegistered('Escape')) globalShortcut.unregister('Escape')
  }
}

function send(win: BrowserWindow, mode: OverlayMode): void {
  if (!win.isDestroyed()) win.webContents.send(CHANNEL.mode, mode)
}
