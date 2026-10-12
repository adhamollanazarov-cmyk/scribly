import { render } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import { handRuns } from './handRuns'
import { Handwriting } from './handwriting'
import { boardFrame } from './frame'
import { penAt } from './geometry'
import type { Primitive } from '../lesson/types'

describe('font measurements and exponents', () => {
  it('renders negative exponents with ordinary Caveat glyphs at superscript size', () => {
    expect(handRuns('3 × 10⁻⁹ C')).toEqual([
      { text: '3 × 10', position: 'normal' },
      { text: '-9', position: 'super' },
      { text: ' C', position: 'normal' },
    ])
    const { container } = render(
      <svg>
        <text>
          <Handwriting text="10⁻⁹ m₂" svg />
        </text>
      </svg>,
    )
    expect(container.querySelector('[baseline-shift="super"]')?.textContent).toBe('-9')
    expect(container.querySelector('[baseline-shift="sub"]')?.textContent).toBe('2')
    expect(container.textContent).not.toContain('⁻')
  })

  it('uses actual full-content bounds for highlight loops', () => {
    const text: Primitive = { id: 't', type: 'text', x: 100, y: 200, text: 'iiiWWW' }
    const highlight: Primitive = { id: 'h', type: 'highlight', target_id: 't' }
    const actual = { x: 98, y: 170, w: 143, h: 43 }
    const frame = boardFrame([{ draw: [text, highlight] }], 1, null, new Map([['t', actual]]))
    expect(frame.prims[1].target).toEqual(actual)
  })

  it('puts the pen at the revealed glyph advance, rather than a character-count estimate', () => {
    const text: Primitive = { id: 't', type: 'text', x: 100, y: 200, text: 'iW' }
    expect(penAt(text, 0.5, null, { x: 100, y: 170, w: 42, h: 40, advances: [0, 7, 43] })).toEqual([
      107, 200,
    ])
    const formula: Primitive = { id: 'm', type: 'math', x: 100, y: 200, latex: '\\frac{x}{y}' }
    expect(penAt(formula, 0.5, null, { x: 100, y: 145, w: 80, h: 70 })).toEqual([140, 200])
  })
})
