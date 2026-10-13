import { useState } from 'react'
import { t } from '../i18n'
import { SAMPLES } from '../lesson/samples'
import { LIBRARY_TOPICS } from '../overlay/settings'
import type { LessonRequest } from '../lesson/types'

export function LessonForm({ onSubmit }: { onSubmit: (request: LessonRequest) => void }) {
  const [type, setType] = useState<LessonRequest['type']>('topic')
  const [text, setText] = useState('')

  const submit = (event: { preventDefault(): void }) => {
    event.preventDefault()
    if (text.trim()) onSubmit({ type, text: text.trim() })
  }
  const pick = (request: LessonRequest) => {
    setType(request.type)
    setText(request.text)
    onSubmit(request)
  }

  return (
    <form className="lesson-form" onSubmit={submit}>
      <label className="form-label" htmlFor="lesson-text">
        {t('form.label')}
      </label>
      <div className="segmented" role="radiogroup" aria-label={t('form.label')}>
        {(['topic', 'problem'] as const).map((value) => (
          <label key={value} className={type === value ? 'on' : ''}>
            <input
              type="radio"
              name="lesson-type"
              value={value}
              checked={type === value}
              onChange={() => setType(value)}
            />
            {t(value === 'topic' ? 'form.topic' : 'form.problem')}
          </label>
        ))}
      </div>
      <div className="form-row">
        <textarea
          id="lesson-text"
          value={text}
          rows={type === 'problem' ? 3 : 1}
          maxLength={5000}
          placeholder={t(type === 'topic' ? 'form.placeholder.topic' : 'form.placeholder.problem')}
          onChange={(e) => setText(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === 'Enter' && !e.shiftKey) submit(e)
          }}
        />
        <button type="submit" className="btn primary" disabled={!text.trim()}>
          {t('form.submit')}
        </button>
      </div>
      <div className="samples">
        <span className="muted">{t('form.samples')}</span>
        {SAMPLES.map((sample) => (
          <button
            key={sample.label}
            type="button"
            className="chip"
            onClick={() => pick(sample.request)}
          >
            {t(sample.label)}
          </button>
        ))}
        {/* Mock mode serves these offline library lessons (same list as the tray's Demo topics). */}
        <select
          className="chip"
          aria-label={t('form.demoTopics')}
          value=""
          onChange={(e) => e.target.value && pick({ type: 'topic', text: e.target.value })}
        >
          <option value="">{t('form.demoPick')}</option>
          {LIBRARY_TOPICS.map((topic) => (
            <option key={topic.key} value={topic.title}>
              {topic.title}
            </option>
          ))}
        </select>
      </div>
    </form>
  )
}
