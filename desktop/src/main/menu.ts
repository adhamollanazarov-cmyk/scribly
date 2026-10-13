import type { MenuItemConstructorOptions } from 'electron'
import { t } from '../../../web/src/i18n'
import {
  LIBRARY_TOPICS,
  SPEEDS,
  VOICES,
  type OverlaySettings,
  type SubtitleLanguage,
} from '../../../web/src/overlay/settings'

export const HOTKEY = 'CommandOrControl+Shift+Space'

export interface MenuActions {
  explain: () => void
  update: (patch: Partial<OverlaySettings>) => void
  quit: () => void
}

const SUBTITLE_LABELS: [SubtitleLanguage, string][] = [
  ['uz', t('subtitles.uz')],
  ['ru', t('subtitles.ru')],
  ['off', t('subtitles.off')],
]

/** The tray menu: explain, settings (voice, speed, subtitles, demo topic, launch at login), quit. */
export function trayMenu(
  settings: OverlaySettings,
  act: MenuActions,
): MenuItemConstructorOptions[] {
  const radio = <T>(
    value: T,
    current: T,
    label: string,
    patch: Partial<OverlaySettings>,
  ): MenuItemConstructorOptions => ({
    label,
    type: 'radio',
    checked: value === current,
    click: () => act.update(patch),
  })

  return [
    { label: t('tray.explain'), accelerator: HOTKEY, click: act.explain },
    { type: 'separator' },
    {
      label: t('tray.settings'),
      submenu: [
        {
          label: t('tray.voice'),
          submenu: VOICES.map((v) => radio(v.id, settings.voice, v.label, { voice: v.id })),
        },
        {
          label: t('tray.speed'),
          submenu: SPEEDS.map((s) => radio(s, settings.speed, `${s}×`, { speed: s })),
        },
        {
          label: t('tray.subtitles'),
          submenu: SUBTITLE_LABELS.map(([lang, label]) =>
            radio(lang, settings.subtitles, label, { subtitles: lang }),
          ),
        },
        {
          // Mock mode until Phase 4 reads the topic from the captured region.
          label: t('tray.demoTopics'),
          submenu: [
            radio('', settings.demoTopic, t('tray.demoDefault'), { demoTopic: '' }),
            ...LIBRARY_TOPICS.map((topic) =>
              radio(topic.key, settings.demoTopic, topic.title, { demoTopic: topic.key }),
            ),
          ],
        },
        { type: 'separator' },
        {
          label: t('tray.login'),
          type: 'checkbox',
          checked: settings.launchAtLogin,
          click: (item) => act.update({ launchAtLogin: item.checked }),
        },
      ],
    },
    { type: 'separator' },
    { label: t('tray.quit'), click: act.quit },
  ]
}
