// Overlay settings, chosen in the tray menu and stored by Electron's main process
// (desktop/ bundles this file). Pure: no DOM or Node imports.

export const VOICES = [
  { id: 'en-US-AriaNeural', label: 'Aria (US)' },
  { id: 'en-US-JennyNeural', label: 'Jenny (US)' },
  { id: 'en-US-GuyNeural', label: 'Guy (US)' },
  { id: 'en-GB-SoniaNeural', label: 'Sonia (UK)' },
] as const
export type Voice = (typeof VOICES)[number]['id']

export const SPEEDS = [0.75, 1, 1.25, 1.5] as const
export const SUBTITLE_LANGUAGES = ['uz', 'ru', 'off'] as const
export type SubtitleLanguage = (typeof SUBTITLE_LANGUAGES)[number]

export interface OverlaySettings {
  voice: Voice
  speed: number
  subtitles: SubtitleLanguage
  /** Start Scribbly when Windows starts. Off unless the user turns it on. */
  launchAtLogin: boolean
}

export const DEFAULT_SETTINGS: OverlaySettings = {
  voice: 'en-US-AriaNeural',
  speed: 1,
  subtitles: 'uz',
  launchAtLogin: false,
}

/** Settings from untrusted JSON: unknown or invalid fields fall back to the defaults. */
export function sanitizeSettings(value: unknown): OverlaySettings {
  const raw = typeof value === 'object' && value !== null ? (value as Record<string, unknown>) : {}
  const pick = <T>(allowed: readonly T[], v: unknown, fallback: T): T =>
    allowed.includes(v as T) ? (v as T) : fallback
  return {
    voice: pick(
      VOICES.map((v) => v.id),
      raw.voice,
      DEFAULT_SETTINGS.voice,
    ),
    speed: pick(SPEEDS, raw.speed, DEFAULT_SETTINGS.speed),
    subtitles: pick(SUBTITLE_LANGUAGES, raw.subtitles, DEFAULT_SETTINGS.subtitles),
    launchAtLogin: raw.launchAtLogin === true,
  }
}

/** The next speed in the pill's cycle. */
export function nextSpeed(speed: number): number {
  const i = SPEEDS.findIndex((s) => s > speed + 1e-9)
  return SPEEDS[i === -1 ? 0 : i]
}
