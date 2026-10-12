// The only API the overlay page gets: `window.scribbly` (see web/src/overlay/bridge.ts).
// Runs sandboxed with context isolation; no Node APIs reach the page.
import { contextBridge, ipcRenderer } from 'electron'
import type { OverlayBridge, OverlayMode } from '../../../web/src/overlay/bridge'
import type { Rect } from '../../../web/src/overlay/geometry'
import { CHANNEL } from '../shared/channels'

let last: OverlayMode | null = null
const listeners = new Set<(mode: OverlayMode) => void>()

ipcRenderer.on(CHANNEL.mode, (_event, mode: OverlayMode) => {
  last = mode
  for (const listener of listeners) listener(mode)
})

const bridge: OverlayBridge = {
  onMode(listener) {
    listeners.add(listener)
    if (last) listener(last) // main may send before React subscribes
    return () => {
      listeners.delete(listener)
    }
  },
  selectRegion(region: Rect | null) {
    ipcRenderer.send(CHANNEL.select, region)
  },
  setInteractive(interactive: boolean) {
    ipcRenderer.send(CHANNEL.interactive, interactive === true)
  },
  closeLesson() {
    ipcRenderer.send(CHANNEL.close)
  },
}

contextBridge.exposeInMainWorld('scribbly', bridge)
