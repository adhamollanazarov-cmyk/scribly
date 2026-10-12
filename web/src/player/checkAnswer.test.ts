import { describe, expect, it } from 'vitest'
import type { Checkpoint } from '../lesson/types'
import { checkAnswer, parseNumber } from './checkAnswer'

const number: Checkpoint = {
  question: 'R?',
  type: 'number',
  answer: 300,
  tolerance: 0.02,
  unit: 'Ω',
}
const choice: Checkpoint = { question: 'Flux?', type: 'choice', choices: ['a', 'b'], answer: 1 }

describe('checkAnswer', () => {
  it.each([
    ['3.4', 3.4],
    ['3,4', 3.4],
    [' −2 ', -2],
    ['3e-9', 3e-9],
    ['3×10^-9', 3e-9],
    ['3 * 10^2', 300],
    ['abc', null],
    ['', null],
  ])('reads %j as %s', (input, value) => {
    expect(parseNumber(input)).toBe(value)
  })

  it('accepts numbers within the relative tolerance', () => {
    expect(checkAnswer(number, '305').correct).toBe(true)
    expect(checkAnswer(number, '310').correct).toBe(false)
    expect(checkAnswer(number, 'three hundred')).toEqual({ correct: false, expected: '300 Ω' })
  })

  it('checks a choice by index and shows the right one', () => {
    expect(checkAnswer(choice, 1)).toEqual({ correct: true, expected: 'b' })
    expect(checkAnswer(choice, 0).correct).toBe(false)
  })

  it('uses an absolute tolerance around zero', () => {
    const zero = { ...number, answer: 0 }
    expect(checkAnswer(zero, '0.01').correct).toBe(true)
    expect(checkAnswer(zero, '0.5').correct).toBe(false)
  })
})
