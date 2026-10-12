import { BrowserWindow, type Display, type WebPreferences } from 'electron'

/** Locked-down renderer: no Node, isolated sandboxed preload, autoplay for narration. */
export function secureWebPreferences(preload: string, devTools: boolean): WebPreferences {
  return {
    preload,
    contextIsolation: true,
    nodeIntegration: false,
    nodeIntegrationInWorker: false,
    sandbox: true,
    webSecurity: true,
    allowRunningInsecureContent: false,
    webviewTag: false,
    spellcheck: false,
    devTools,
    // The hotkey is not a page gesture, but the lesson must speak.
    autoplayPolicy: 'no-user-gesture-required',
  }
}

/**
 * A transparent, frameless, always-on-top window covering exactly one display. One window
 * per display: a window spanning monitors with different scale factors is mis-sized on
 * Windows, and per-display windows keep CSS pixels equal to that display's DIPs.
 */
export function createOverlayWindow(
  display: Display,
  preload: string,
  devTools: boolean,
): BrowserWindow {
  const win = new BrowserWindow({
    ...display.bounds,
    show: false,
    frame: false,
    transparent: true,
    backgroundColor: '#00000000',
    resizable: false,
    movable: false,
    minimizable: false,
    maximizable: false,
    fullscreenable: false,
    skipTaskbar: true,
    hasShadow: false,
    alwaysOnTop: true,
    thickFrame: false,
    roundedCorners: false,
    title: 'Scribbly',
    webPreferences: secureWebPreferences(preload, devTools),
  })
  win.setAlwaysOnTop(true, 'screen-saver')
  // Mixed DPI: apply the bounds again once the window lives on its display.
  win.setBounds(display.bounds)
  win.setMenu(null)
  return win
}
