// What Scribbly writes on the board the moment a request is sent, before step 1 arrives:
// the problem statement (or topic) and the given values it can read from the text.

import type { LessonRequest, TextPrim } from './types'

// prettier-ignore
const UNITS = [
  'm/s²', 'm/s\\^2', 'm/s2', 'm/s', 'km/h', 'N/C', 'V/m', 'F/m', 'N·m', 'N\\*m', 'kg·m/s',
  'nC', 'μC', 'µC', 'uC', 'mC', 'pC', 'C', 'km', 'cm', 'mm', 'nm', 'm', 'kg', 'g', 'ms', 's',
  'kN', 'N', 'kV', 'mV', 'V', 'mA', 'A', 'kΩ', 'MΩ', 'Ω', 'ohms', 'ohm', 'kJ', 'eV', 'J',
  'kW', 'W', 'Hz', 'μF', 'µF', 'uF', 'nF', 'pF', 'F', 'mT', 'T', 'K', '°C', '°', 'rad', 'Pa',
  'L', 'mH', 'H',
]

const NUMBER = String.raw`[+\-−]?\d+(?:[.,]\d+)?(?:\s*(?:[eE][+\-−]?\d+|[×x*]\s*10\^?[+\-−]?\d+))?`
const UNIT = `(?:${UNITS.join('|')})(?![A-Za-zΩ°²])`
const NAME = String.raw`(?:epsilon_0|[A-Za-zΔθφωλμεσρτ][A-Za-z0-9_]{0,6})`
const NAMED = new RegExp(String.raw`(?<![\w.])(${NAME})\s*=\s*(${NUMBER})\s*(${UNIT})?`, 'gu')
const BARE = new RegExp(String.raw`(?<![\w.=])(${NUMBER})\s*(${UNIT})`, 'gu')
const MAX_GIVENS = 6

export interface Given {
  name: string | null
  value: string
  unit: string
}

export function extractGivens(text: string): Given[] {
  const givens: Given[] = []
  const taken: [number, number][] = []
  for (const m of text.matchAll(NAMED)) {
    taken.push([m.index, m.index + m[0].length])
    givens.push({ name: m[1], value: m[2], unit: m[3] ?? '' })
  }
  for (const m of text.matchAll(BARE)) {
    const inside = taken.some(([a, b]) => m.index >= a && m.index < b)
    if (!inside) givens.push({ name: null, value: m[1], unit: m[2] })
  }
  const seen = new Set<string>()
  return givens
    .filter((g) => {
      const key = formatGiven(g)
      return !seen.has(key) && seen.add(key)
    })
    .slice(0, MAX_GIVENS)
}

// prettier-ignore
const SUPERSCRIPT: Record<string, string> = {
  '-': '⁻', '−': '⁻', '+': '⁺', '0': '⁰', '1': '¹', '2': '²', '3': '³', '4': '⁴', '5': '⁵',
  '6': '⁶', '7': '⁷', '8': '⁸', '9': '⁹',
}

function prettyNumber(value: string): string {
  return value
    .replace(/\s+/g, '')
    .replace(/^-/, '−')
    .replace(/(?:[eE]|[×x*]10\^?)([+\-−]?\d+)$/, (_, exp: string) => {
      const digits = [...exp.replace(/^\+/, '')].map((c) => SUPERSCRIPT[c] ?? c).join('')
      return ` × 10${digits}`
    })
}

function prettyUnit(unit: string): string {
  return unit
    .replace(/^ohms?$/, 'Ω')
    .replace(/^u([CF])$/, 'μ$1')
    .replace(/\^2|2$/, '²')
    .replace(/\*/g, '·')
}

function prettyName(name: string): string {
  return name === 'epsilon_0' ? 'ε₀' : name
}

export function formatGiven(g: Given): string {
  const quantity = `${prettyNumber(g.value)}${g.unit ? ' ' + prettyUnit(g.unit) : ''}`
  return g.name ? `${prettyName(g.name)} = ${quantity}` : quantity
}

/** Greedy word wrap; if the text does not fit, the last line gets a trailing "…". */
export function wrapText(text: string, width: number, maxLines: number): string[] {
  const lines: string[] = []
  let line = ''
  for (const word of text.split(/\s+/).filter(Boolean)) {
    if (line && (line + ' ' + word).length > width) {
      lines.push(line)
      line = word
    } else {
      line = line ? line + ' ' + word : word
    }
  }
  if (line) lines.push(line)
  if (lines.length <= maxLines) return lines
  const kept = lines.slice(0, maxLines)
  kept[maxLines - 1] += ' …'
  return kept
}

export interface IntroLabels {
  problem: string
  topic: string
  given: string
}

export function introPrimitives(request: LessonRequest, labels: IntroLabels): TextPrim[] {
  const isTopic = request.type === 'topic'
  const prims: TextPrim[] = [
    {
      id: 'intro-title',
      type: 'text',
      x: 80,
      y: 120,
      text: isTopic ? labels.topic : labels.problem,
      size: 52,
      color: 'accent',
    },
  ]
  const lines = isTopic ? wrapText(request.text, 38, 3) : wrapText(request.text, 56, 8)
  const size = isTopic ? 64 : 40
  lines.forEach((text, i) => {
    prims.push({ id: `intro-line-${i}`, type: 'text', x: 80, y: 200 + i * size * 1.35, text, size })
  })
  const givens = isTopic ? [] : extractGivens(request.text)
  if (givens.length) {
    prims.push({ id: 'intro-given', type: 'text', x: 1160, y: 120, text: labels.given, size: 52 })
    givens.forEach((g, i) => {
      const y = 200 + i * 62
      const text = formatGiven(g)
      prims.push({
        id: `intro-given-${i}`,
        type: 'text',
        x: 1180,
        y,
        text,
        size: 44,
        color: 'accent',
      })
    })
  }
  return prims
}
