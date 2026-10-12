import { mkdirSync, readFileSync, writeFileSync } from 'node:fs'
import { dirname } from 'node:path'
import { sanitizeSettings, type OverlaySettings } from '../../../web/src/overlay/settings'

/** Settings from the user's settings file; a missing or broken file gives the defaults. */
export function loadSettings(file: string): OverlaySettings {
  try {
    return sanitizeSettings(JSON.parse(readFileSync(file, 'utf8')))
  } catch {
    return sanitizeSettings(null)
  }
}

export function saveSettings(file: string, settings: OverlaySettings): void {
  mkdirSync(dirname(file), { recursive: true })
  writeFileSync(file, JSON.stringify(sanitizeSettings(settings), null, 2) + '\n', 'utf8')
}
