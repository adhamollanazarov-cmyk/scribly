import { t } from '../i18n'
import type { PlayerState } from '../player/engine'
import { nextSpeed } from './settings'

interface Props {
  state: PlayerState
  onPlay: () => void
  onPause: () => void
  onReplay: () => void
  onSpeed: (speed: number) => void
  onClose: () => void
}

/** The overlay's only controls: pause/resume, replay step, speed, close. */
export function Pill({ state, onPlay, onPause, onReplay, onSpeed, onClose }: Props) {
  const running = state.status === 'running'
  const playing = running && !state.paused
  return (
    <div className="pill" role="toolbar" aria-label={t('controls.label')} data-interactive>
      {playing ? (
        <button type="button" onClick={onPause} title={t('controls.pause')}>
          <span aria-hidden="true">⏸</span>
          <span className="sr-only">{t('controls.pause')}</span>
        </button>
      ) : (
        <button
          type="button"
          onClick={onPlay}
          disabled={!state.steps.length}
          title={t('controls.play')}
        >
          <span aria-hidden="true">▶</span>
          <span className="sr-only">{t('controls.play')}</span>
        </button>
      )}
      <button
        type="button"
        onClick={onReplay}
        disabled={!running || !state.steps.length}
        title={t('controls.replay')}
      >
        <span aria-hidden="true">↺</span>
        <span className="sr-only">{t('controls.replay')}</span>
      </button>
      <button
        type="button"
        className="pill-speed"
        onClick={() => onSpeed(nextSpeed(state.speed))}
        title={t('controls.speed')}
        aria-label={`${t('controls.speed')} ${state.speed}×`}
      >
        {state.speed}×
      </button>
      <button type="button" onClick={onClose} title={t('overlay.close')}>
        <span aria-hidden="true">✕</span>
        <span className="sr-only">{t('overlay.close')}</span>
      </button>
    </div>
  )
}
