import { t } from '../i18n'
import type { PlayerState } from '../player/engine'
import type { SubtitleSettings } from './Controls'

function statusLine(state: PlayerState): string | null {
  if (state.error) return state.error
  if (state.status === 'finished') return t('status.done')
  if (state.status === 'running' && state.stage === 'waiting') {
    return t(state.steps.length ? 'status.waiting' : 'status.preparing')
  }
  return null
}

export function Subtitles({ state, settings }: { state: PlayerState; settings: SubtitleSettings }) {
  const step = state.status === 'running' ? state.steps[state.index] : undefined
  const status = statusLine(state)
  const second = step && settings.second !== 'off' ? step.subtitles?.[settings.second] : null
  const noAudio = state.stage === 'playing' && !state.audioActive
  return (
    <div className="subtitles" aria-live="polite">
      {step ? (
        <>
          {(settings.english || noAudio) && <p className="sub-en">{step.say}</p>}
          {noAudio && <p className="badge warn">{t('warning.audio')}</p>}
          {second && (
            <p className="sub-second" lang={settings.second}>
              {second}
            </p>
          )}
          {step.warning === 'unverified' && (
            <p className="badge warn">⚠ {t('warning.unverified')}</p>
          )}
        </>
      ) : (
        <p className={state.error ? 'sub-error' : 'muted'}>{status ?? t('board.empty')}</p>
      )}
    </div>
  )
}
