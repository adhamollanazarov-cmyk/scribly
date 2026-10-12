import { useState, type FormEvent } from 'react'
import { t } from '../i18n'
import type { Checkpoint } from '../lesson/types'
import type { AnswerResult } from '../player/checkAnswer'

interface Props {
  checkpoint: Checkpoint
  feedback: AnswerResult | null
  onAnswer: (input: number | string) => void
  onNext: () => void
}

/** Phase 2: one answer, feedback, then on. Re-explaining wrong answers is Phase 3. */
export function CheckpointCard({ checkpoint, feedback, onAnswer, onNext }: Props) {
  const [typed, setTyped] = useState('')
  const answered = feedback !== null
  const submit = (event: FormEvent) => {
    event.preventDefault()
    if (typed.trim()) onAnswer(typed)
  }

  return (
    <section className="checkpoint" aria-label={t('checkpoint.title')}>
      <h2>{t('checkpoint.title')}</h2>
      <p className="question">{checkpoint.question}</p>
      {checkpoint.type === 'choice' ? (
        <div className="choices">
          {(checkpoint.choices ?? []).map((choice, i) => (
            <button
              key={i}
              type="button"
              className={'btn choice' + (answered && i === checkpoint.answer ? ' right' : '')}
              disabled={answered}
              onClick={() => onAnswer(i)}
            >
              {choice}
            </button>
          ))}
        </div>
      ) : (
        <form className="number-answer" onSubmit={submit}>
          <label>
            {t('checkpoint.answer')}
            <input
              inputMode="decimal"
              value={typed}
              disabled={answered}
              onChange={(e) => setTyped(e.target.value)}
            />
          </label>
          {checkpoint.unit && <span className="unit">{checkpoint.unit}</span>}
          <button type="submit" className="btn" disabled={answered || !typed.trim()}>
            {t('checkpoint.check')}
          </button>
        </form>
      )}
      {feedback && (
        <div className={'feedback ' + (feedback.correct ? 'right' : 'wrong')} role="status">
          {feedback.correct ? (
            <strong>{t('checkpoint.correct')}</strong>
          ) : (
            <>
              <strong>
                {t('checkpoint.wrong')} {feedback.expected}
              </strong>
              {checkpoint.hint && (
                <p>
                  {t('checkpoint.hint')} {checkpoint.hint}
                </p>
              )}
            </>
          )}
        </div>
      )}
      <div className="checkpoint-actions">
        <button type="button" className={'btn' + (answered ? ' primary' : '')} onClick={onNext}>
          {t(answered ? 'checkpoint.continue' : 'checkpoint.skip')}
        </button>
      </div>
    </section>
  )
}
