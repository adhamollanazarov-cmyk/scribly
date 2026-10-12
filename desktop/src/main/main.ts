// Scribbly desktop: a tray app. Ctrl+Shift+Space → select a region → a lesson is drawn on
// top of it. No window exists until the hotkey; nothing is captured without it.
import { join } from 'node:path'
import {
  app,
  globalShortcut,
  ipcMain,
  Menu,
  nativeImage,
  session,
  Tray,
  type IpcMainEvent,
} from 'electron'
import { t } from '../../../web/src/i18n'
import { sanitizeSettings, type OverlaySettings } from '../../../web/src/overlay/settings'
import { CHANNEL } from '../shared/channels'
import { HOTKEY, trayMenu } from './menu'
import { OverlayController } from './overlay'
import { handleScheme, PAGE_URL, registerScheme } from './protocol'
import { loadSettings, saveSettings } from './settingsStore'

const E2E = process.env.SCRIBBLY_E2E === '1'
const SERVER = process.env.SCRIBBLY_SERVER ?? 'http://127.0.0.1:8000'
// Dev: load the page from Vite (`npm run dev` in web/) instead of the built files.
const DEV_URL = process.env.SCRIBBLY_RENDERER_URL

if (process.env.SCRIBBLY_USER_DATA) app.setPath('userData', process.env.SCRIBBLY_USER_DATA)
registerScheme()

const resources = app.isPackaged ? process.resourcesPath : join(__dirname, '..')
const rendererRoot = app.isPackaged
  ? join(process.resourcesPath, 'renderer')
  : join(__dirname, '..', '..', 'web', 'dist')
const trayIcon = app.isPackaged
  ? join(resources, 'icons', 'tray.png')
  : join(resources, 'resources', 'tray.png')
const settingsFile = () => join(app.getPath('userData'), 'settings.json')

let tray: Tray | null = null
let settings: OverlaySettings = sanitizeSettings(null)

const overlay = new OverlayController({
  preload: join(__dirname, 'preload.js'),
  devTools: !app.isPackaged,
  load: (win) => win.loadURL(DEV_URL ? new URL('/overlay.html', DEV_URL).toString() : PAGE_URL),
  settings: () => settings,
  notify: (message) => tray?.displayBalloon({ title: 'Scribbly', content: message }),
})

function lockDown(): void {
  app.on('web-contents-created', (_event, contents) => {
    contents.on('will-navigate', (event) => event.preventDefault())
    contents.on('will-attach-webview', (event) => event.preventDefault())
    contents.setWindowOpenHandler(() => ({ action: 'deny' }))
  })
  session.defaultSession.setPermissionRequestHandler((_wc, _permission, done) => done(false))
  session.defaultSession.setPermissionCheckHandler(() => false)
}

function applyLoginItem(): void {
  // Only the installed app registers itself; a dev run must not add electron.exe to startup.
  if (app.isPackaged) app.setLoginItemSettings({ openAtLogin: settings.launchAtLogin })
}

function updateSettings(patch: Partial<OverlaySettings>): void {
  settings = sanitizeSettings({ ...settings, ...patch })
  saveSettings(settingsFile(), settings)
  if ('launchAtLogin' in patch) applyLoginItem()
  buildTrayMenu()
}

function buildTrayMenu(): void {
  const template = trayMenu(settings, {
    explain: () => overlay.startSelection(),
    update: updateSettings,
    quit: () => app.quit(),
  })
  tray?.setContextMenu(Menu.buildFromTemplate(template))
}

function listen(): void {
  const guard =
    <A extends unknown[]>(handler: (event: IpcMainEvent, ...args: A) => void) =>
    (event: IpcMainEvent, ...args: A) => {
      if (overlay.owns(event.sender)) handler(event, ...args)
    }
  ipcMain.on(
    CHANNEL.select,
    guard((event, region: unknown) => void overlay.select(event.sender, region)),
  )
  ipcMain.on(
    CHANNEL.interactive,
    guard((event, on: unknown) => overlay.setInteractive(event.sender, on === true)),
  )
  ipcMain.on(
    CHANNEL.close,
    guard((event) => overlay.closeLesson(event.sender)),
  )
}

function start(): void {
  lockDown()
  if (!DEV_URL) handleScheme(rendererRoot, SERVER)
  settings = loadSettings(settingsFile())
  applyLoginItem()
  listen()

  tray = new Tray(nativeImage.createFromPath(trayIcon))
  tray.setToolTip(t('tray.tooltip'))
  tray.on('click', () => tray?.popUpContextMenu())
  buildTrayMenu()

  if (!globalShortcut.register(HOTKEY, () => overlay.startSelection())) {
    tray.displayBalloon({ title: 'Scribbly', content: t('tray.hotkeyTaken') })
  }

  if (E2E) {
    // Test hooks for the Playwright smoke test only (SCRIBBLY_E2E=1).
    Object.assign(globalThis, {
      __scribblyTest: {
        startSelection: () => overlay.startSelection(),
        hasTray: () => tray !== null && !tray.isDestroyed(),
        hotkeyRegistered: () => globalShortcut.isRegistered(HOTKEY),
        overlayActive: () => overlay.active,
        settings: () => settings,
      },
    })
  }
}

if (!E2E && !app.requestSingleInstanceLock()) {
  app.quit()
} else {
  app.on('second-instance', () => overlay.startSelection())
  // A tray app: closing the overlay must not quit.
  app.on('window-all-closed', () => {})
  app.on('will-quit', () => globalShortcut.unregisterAll())
  void app.whenReady().then(start)
}
