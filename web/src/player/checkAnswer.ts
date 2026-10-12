import type { Checkpoint } from '../lesson/types'

export interface AnswerResult {
  correct: boolean
  /** The correct answer, as shown to the student. */
  expected: string
}

const DEFAULT_TOLERANCE = 0.02

/** Read a typed number: "3.4", "3,4", "−2", "3e-9", "3×10^-9", "3*10^-9". */
export function parseNumber(input: string): number | null {
  const s = input
    .trim()
    .replace(/[−–]/g, '-')
    .replace(/\s+/g, '')
    .replace(/(\d),(\d)/g, '$1.$2')
    .replace(/[×x*]10\^?/i, 'e')
  if (!/^[+-]?(\d+\.?\d*|\.\d+)(e[+-]?\d+)?$/i.test(s)) return null
  const value = Number(s)
  return Number.isFinite(value) ? value : null
}

export function checkAnswer(checkpoint: Checkpoint, input: number | string): AnswerResult {
  if (checkpoint.type === 'choice') {
    const choices = checkpoint.choices ?? []
    return { correct: input === checkpoint.answer, expected: choices[checkpoint.answer] ?? '' }
  }
  const unit = checkpoint.unit ? ` ${checkpoint.unit}` : ''
  const expected = `${checkpoint.answer}${unit}`
  const value = typeof input === 'number' ? input : parseNumber(input)
  if (value === null) return { correct: false, expected }
  const tolerance = checkpoint.tolerance ?? DEFAULT_TOLERANCE
  // The contract specifies relative tolerance. Zero has no implicit absolute
  // allowance: 0.02 C and 0.02 nC would represent very different errors.
  const allowed = tolerance * Math.abs(checkpoint.answer)
  return { correct: Math.abs(value - checkpoint.answer) <= allowed, expected }
}
