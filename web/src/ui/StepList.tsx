import { t } from '../i18n'
import type { PlayerState } from '../player/engine'

const PREVIEW_WORDS = 8

function preview(say: string): string {
  const words = say.split(/\s+/)
  return words.length > PREVIEW_WORDS ? words.slice(0, PREVIEW_WORDS).join(' ') + '…' : say
}

export function StepList({ state, onJump }: { state: PlayerState; onJump: (i: number) => void }) {
  const pending = Math.max(0, (state.meta?.step_count ?? 0) - state.steps.length)
  const generating = state.status === 'running' && !state.streamDone
  return (
    <nav className="step-list" aria-label={t('steps.title')}>
      <h2>{t('steps.title')}</h2>
      <ol>
        {state.steps.map((step, i) => {
          const record = state.records[step.id]
          const current = state.status === 'running' && i === state.index
          const status = current ? 'current' : record ? 'done' : 'pending'
          return (
            <li
              key={step.id}
              data-step-id={step.id}
              data-status={status}
              data-audio={record?.audio ?? ''}
              data-drawn={record?.drawn ? 'true' : 'false'}
            >
              <button
                type="button"
                onClick={() => onJump(i)}
                aria-current={current ? 'step' : undefined}
              >
                <span className="step-num">{i + 1}</span>
                <span className="step-text">
                  {step.kind === 'checkpoint' && <span aria-hidden="true">❓ </span>}
                  {preview(step.say)}
                </span>
                {record && (
                  <span className="step-check" aria-hidden="true">
                    ✓
                  </span>
                )}
              </button>
            </li>
          )
        })}
        {Array.from({ length: generating ? Math.max(pending, 1) : 0 }, (_, i) => (
          <li key={`pending-${i}`} className="placeholder" aria-hidden="true">
            <span className="step-num">{state.steps.length + i + 1}</span>
            <span className="step-text muted">{t('steps.pending')}</span>
          </li>
        ))}
      </ol>
    </nav>
  )
}
