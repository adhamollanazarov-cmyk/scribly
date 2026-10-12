import { mkdtempSync, readFileSync, writeFileSync } from 'node:fs'
import { tmpdir } from 'node:os'
import { join, resolve, sep } from 'node:path'
import type { MenuItemConstructorOptions } from 'electron'
import { describe, expect, it, vi } from 'vitest'
import { DEFAULT_SETTINGS } from '../../../web/src/overlay/settings'
import { pickSource } from './capture'
import { trayMenu } from './menu'
import { CSP, resolveInside, routeFor } from './protocol'
import { loadSettings, saveSettings } from './settingsStore'
import { secureWebPreferences } from './windows'

const sub = (item: MenuItemConstructorOptions | undefined) =>
  (item?.submenu ?? []) as MenuItemConstructorOptions[]

describe('tray menu', () => {
  const actions = () => ({ explain: vi.fn(), update: vi.fn(), quit: vi.fn() })

  it('offers explain, settings and quit', () => {
    const menu = trayMenu(DEFAULT_SETTINGS, actions())
    expect(menu.filter((i) => i.label).map((i) => i.label)).toEqual([
      'Explain a region',
      'Settings',
      'Quit Scribbly',
    ])
    expect(menu[0].accelerator).toBe('CommandOrControl+Shift+Space')
  })

  it('has voice, speed and subtitle radio groups reflecting the settings', () => {
    const settings = sub(trayMenu(DEFAULT_SETTINGS, actions())[2])
    const [voice, speed, subtitles] = settings
    expect(voice.label).toBe('Voice')
    expect(sub(voice).find((i) => i.checked)?.label).toBe('Aria (US)')
    expect(sub(speed).map((i) => i.label)).toEqual(['0.75×', '1×', '1.25×', '1.5×'])
    expect(sub(speed).find((i) => i.checked)?.label).toBe('1×')
    expect(sub(subtitles).find((i) => i.checked)?.label).toBe("O'zbekcha")
  })

  it('launch at login is an unchecked checkbox by default', () => {
    const login = sub(trayMenu(DEFAULT_SETTINGS, actions())[2]).find(
      (i) => i.label === 'Launch at login',
    )
    expect(login).toMatchObject({ type: 'checkbox', checked: false })
  })

  it('reports setting changes and actions', () => {
    const act = actions()
    const menu = trayMenu(DEFAULT_SETTINGS, act)
    const click = (item: MenuItemConstructorOptions, checked = true) =>
      (item.click as (item: { checked: boolean }) => void)({ checked })
    const [voice, speed, subtitles] = sub(menu[2])
    click(sub(voice)[3])
    click(sub(speed)[3])
    click(sub(subtitles)[1])
    click(sub(menu[2]).at(-1)!)
    expect(act.update.mock.calls).toEqual([
      [{ voice: 'en-GB-SoniaNeural' }],
      [{ speed: 1.5 }],
      [{ subtitles: 'ru' }],
      [{ launchAtLogin: true }],
    ])
    click(menu[0])
    click(menu.at(-1)!)
    expect(act.explain).toHaveBeenCalledOnce()
    expect(act.quit).toHaveBeenCalledOnce()
  })
})

describe('settings file', () => {
  const dir = () => mkdtempSync(join(tmpdir(), 'scribbly-settings-'))

  it('gives the defaults when the file is missing or broken', () => {
    const d = dir()
    expect(loadSettings(join(d, 'missing.json'))).toEqual(DEFAULT_SETTINGS)
    writeFileSync(join(d, 'broken.json'), '{nope')
    expect(loadSettings(join(d, 'broken.json'))).toEqual(DEFAULT_SETTINGS)
  })

  it('round-trips valid settings and drops unknown or invalid ones', () => {
    const file = join(dir(), 'nested', 'settings.json')
    saveSettings(file, { ...DEFAULT_SETTINGS, speed: 1.25, subtitles: 'off' })
    expect(loadSettings(file)).toEqual({ ...DEFAULT_SETTINGS, speed: 1.25, subtitles: 'off' })

    writeFileSync(file, JSON.stringify({ speed: 7, voice: 'x', extra: 'evil' }))
    expect(loadSettings(file)).toEqual(DEFAULT_SETTINGS)
    expect(readFileSync(file, 'utf8')).toContain('evil') // reading never rewrites the file
  })
})

describe('capture source', () => {
  const sources = [{ display_id: '11' }, { display_id: '22' }]

  it('matches the display by id', () => {
    expect(pickSource(sources, 22, 0)).toBe(sources[1])
  })

  it('falls back to the display order only when ids are missing', () => {
    const anonymous = [{ display_id: '' }, { display_id: '' }]
    expect(pickSource(anonymous, 5, 1)).toBe(anonymous[1])
    expect(pickSource(sources, 99, 0)).toBeNull()
  })
})

describe('app:// protocol', () => {
  it('proxies only the two server endpoints, with the right methods', () => {
    const audio = `/audio/${'a'.repeat(64)}.mp3`
    expect(routeFor('POST', '/explain-region')).toEqual({ kind: 'proxy' })
    expect(routeFor('GET', '/explain-region')).toEqual({ kind: 'deny' })
    expect(routeFor('GET', audio)).toEqual({ kind: 'proxy' })
    expect(routeFor('DELETE', audio)).toEqual({ kind: 'deny' })
    expect(routeFor('POST', '/lessons')).toEqual({ kind: 'deny' })
    expect(routeFor('GET', '/audio/../../secret.mp3').kind).toBe('file')
    expect(routeFor('GET', '/health')).toEqual({ kind: 'file', path: 'health' })
  })

  it('serves files from the renderer folder, defaulting to the overlay page', () => {
    expect(routeFor('GET', '/')).toEqual({ kind: 'file', path: 'overlay.html' })
    expect(routeFor('GET', '/assets/a.js')).toEqual({ kind: 'file', path: 'assets/a.js' })
    expect(routeFor('GET', '/%E0%A4%A')).toEqual({ kind: 'deny' })
  })

  it('never resolves a file outside the renderer folder', () => {
    const root = resolve('renderer-root')
    expect(resolveInside(root, 'assets/a.js')).toBe(join(root, 'assets', 'a.js'))
    expect(resolveInside(root, '../secret.txt')).toBeNull()
    expect(resolveInside(root, `assets${sep}..${sep}..${sep}x`)).toBeNull()
    expect(resolveInside(root, 'C:/Windows/win.ini')).toBeNull()
    expect(resolveInside(root, '')).toBeNull()
  })

  it('has a strict content security policy', () => {
    expect(CSP).toContain("default-src 'self'")
    expect(CSP).toContain("script-src 'self'")
    expect(CSP).not.toMatch(/script-src[^;]*unsafe/)
    expect(CSP).toContain("object-src 'none'")
    expect(CSP).toContain("connect-src 'self'")
  })
})

describe('window security', () => {
  it('isolates the page: no Node, sandboxed preload, web security on', () => {
    const prefs = secureWebPreferences('preload.js', false)
    expect(prefs).toMatchObject({
      contextIsolation: true,
      nodeIntegration: false,
      sandbox: true,
      webSecurity: true,
      webviewTag: false,
      devTools: false,
    })
  })
})
