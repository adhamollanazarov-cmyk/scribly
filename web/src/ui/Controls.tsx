import { t } from '../i18n'
import { MAX_SPEED, MIN_SPEED, type PlayerState } from '../player/engine'

export type SubtitleLang = 'off' | 'uz' | 'ru'

export interface SubtitleSettings {
  english: boolean
  second: SubtitleLang
}

interface Props {
  state: PlayerState
  subtitles: SubtitleSettings
  onPlay: () => void
  onPause: () => void
  onRestart: () => void
  onReplay: () => void
  onSpeed: (speed: number) => void
  onSubtitles: (settings: SubtitleSettings) => void
}

export function Controls(props: Props) {
  const { state, subtitles } = props
  const hasSteps = state.steps.length > 0
  const playing = state.status === 'running' && !state.paused
  return (
    <div className="controls" role="toolbar" aria-label={t('controls.label')}>
      {playing ? (
        <button type="button" className="btn" onClick={props.onPause}>
          ⏸ {t('controls.pause')}
        </button>
      ) : (
        <button type="button" className="btn" onClick={props.onPlay} disabled={!hasSteps}>
          ▶ {t('controls.play')}
        </button>
      )}
      <button type="button" className="btn" onClick={props.onRestart} disabled={!hasSteps}>
        ⏮ {t('controls.restart')}
      </button>
      <button
        type="button"
        className="btn"
        onClick={props.onReplay}
        disabled={!hasSteps || state.status !== 'running'}
      >
        ↺ {t('controls.replay')}
      </button>
      <label className="control">
        {t('controls.speed')}
        <input
          type="range"
          min={MIN_SPEED}
          max={MAX_SPEED}
          step={0.1}
          value={state.speed}
          onChange={(e) => props.onSpeed(Number(e.target.value))}
        />
        <output>{state.speed.toFixed(1)}×</output>
      </label>
      <fieldset className="control subtitles-control">
        <legend>{t('controls.subtitles')}</legend>
        <label title={t('controls.english')}>
          <input
            type="checkbox"
            checked={subtitles.english}
            onChange={(e) => props.onSubtitles({ ...subtitles, english: e.target.checked })}
          />
          EN
        </label>
        <select
          aria-label={t('controls.subtitles')}
          value={subtitles.second}
          onChange={(e) =>
            props.onSubtitles({ ...subtitles, second: e.target.value as SubtitleLang })
          }
        >
          <option value="off">{t('subtitles.off')}</option>
          <option value="uz">{t('subtitles.uz')}</option>
          <option value="ru">{t('subtitles.ru')}</option>
        </select>
      </fieldset>
    </div>
  )
}
