import { render } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import { initialState, type PlayerState } from '../player/engine'
import { stepsOf } from '../test/fakes'
import { Subtitles } from './Subtitles'

function playing(ru: string | null): PlayerState {
  const [step] = stepsOf('gauss_law')
  return {
    ...initialState(),
    status: 'running',
    stage: 'playing',
    audioActive: true,
    steps: [{ ...step, subtitles: { uz: 'Salom', ru } }],
    index: 0,
  }
}

const second = (state: PlayerState, lang: 'ru' | 'off') =>
  render(
    <Subtitles state={state} settings={{ english: true, second: lang }} />,
  ).container.querySelector('.sub-second')?.textContent ?? null

describe('Subtitles', () => {
  it('shows the second-language line when the step has one', () => {
    expect(second(playing('Привет'), 'ru')).toBe('Привет')
  })

  it('says the language is missing instead of showing nothing', () => {
    expect(second(playing(null), 'ru')).toBe('Для этого урока нет субтитров на этом языке')
  })

  it('shows no second line when it is turned off', () => {
    expect(second(playing(null), 'off')).toBeNull()
  })
})
