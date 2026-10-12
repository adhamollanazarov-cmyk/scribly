import { render } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import type { Primitive, Step } from '../lesson/types'
import { MASCOT_STATES } from '../mascot/states'
import { Scribbly } from '../mascot/Scribbly'
import { initialState, type PlayerState } from '../player/engine'
import { STREAM_NAMES, stepsOf } from '../test/fakes'
import { Board } from './Board'
import { buildSchedule } from './schedule'

const EVERY_TYPE: Primitive[] = [
  { id: 'pt', type: 'point', x: 100, y: 100, r: 8, label: 'P' },
  { id: 'ln', type: 'line', x1: 100, y1: 200, x2: 300, y2: 200, label: 'L', group: 'g1' },
  { id: 'ar', type: 'arrow', x1: 100, y1: 250, x2: 300, y2: 250, dashed: true },
  { id: 'vc', type: 'vector', from: [100, 300], to: [300, 300], name: 'F = 2 N', color: 'force' },
  { id: 'ci', type: 'circle', cx: 500, cy: 300, r: 80, dashed: true, label: 'surface' },
  { id: 'el', type: 'ellipse', cx: 700, cy: 300, rx: 60, ry: 30 },
  { id: 'rc', type: 'rect', x: 800, y: 200, w: 100, h: 40, label: 'R1' },
  {
    id: 'pl',
    type: 'polyline',
    points: [
      [100, 400],
      [200, 450],
      [300, 400],
    ],
    closed: true,
  },
  {
    id: 'cv',
    type: 'curve',
    points: [
      [100, 500],
      [200, 560],
      [300, 500],
      [400, 560],
    ],
  },
  { id: 'tx', type: 'text', x: 100, y: 650, text: 'flux = Φ' },
  { id: 'mt', type: 'math', x: 400, y: 650, latex: '\\Phi = \\dfrac{Q}{\\varepsilon_0}', size: 40 },
  {
    id: 'sy',
    type: 'symbol',
    x: 100,
    y: 720,
    symbol: '\\Phi',
    meaning: 'electric flux',
    unit: 'N·m²/C',
  },
  { id: 'ax', type: 'axes', x: 1000, y: 400, w: 400, h: 300, xlabel: 't (s)', ylabel: 'v (m/s)' },
  { id: 'pp', type: 'plot', axes_id: 'ax', expr: 'x**2', x_min: 0, x_max: 1 },
  { id: 'hl', type: 'highlight', target_id: 'mt' },
  { id: 'mw', type: 'mark_wrong', target_id: 'rc', reason: 'R1 is 100 ohm, not 10' },
  { id: 'er', type: 'erase', target_id: 'g1' },
]

const step = (draw: Primitive[]): Step => ({
  id: 's1',
  kind: 'explain',
  say: 'x',
  draw,
  audio_url: null,
})

function finished(steps: Step[]): PlayerState {
  return { ...initialState(), status: 'finished', steps, index: steps.length }
}

function playing(steps: Step[], t: number): PlayerState {
  const schedule = buildSchedule(steps[0].draw, 4)
  return { ...initialState(), status: 'running', steps, stage: 'playing', schedule, t }
}

const drawnIds = (container: HTMLElement) =>
  [...container.querySelectorAll('[data-prim]')].map((e) => e.getAttribute('data-prim'))

describe('Board', () => {
  it('renders every drawable primitive type', () => {
    const { container } = render(<Board state={finished([step(EVERY_TYPE)])} title="t" />)

    const drawn = drawnIds(container)
    const skipped = ['pp', 'er', 'ln'] // plot is not drawable; erase draws nothing and hid `ln`
    expect(drawn.sort()).toEqual(
      EVERY_TYPE.map((p) => p.id)
        .filter((id) => !skipped.includes(id))
        .sort(),
    )
    expect(container.querySelectorAll('.katex').length).toBe(2) // math + symbol
    expect(container.querySelector('[data-prim="vc"] text')?.textContent).toBe('F = 2 N')
    expect(container.querySelector('[data-prim="mw"] text')?.textContent).toContain('100 ohm')
    expect(container.querySelector('[data-prim="vc"] path')?.getAttribute('stroke')).toBe(
      'var(--c-force)',
    )
  })

  it('draws a primitive partly, then fully', () => {
    const steps = [step([{ id: 'tx', type: 'text', x: 0, y: 50, text: 'abcdefghij' }])]
    const half = render(<Board state={playing(steps, 0.3)} title="t" />)
    const text = half.container.querySelector('[data-prim="tx"]')!
    expect(text.getAttribute('data-drawn')).toBe('false')
    expect(text.textContent!.length).toBeLessThan(10)
    half.unmount()

    const full = render(<Board state={playing(steps, 4)} title="t" />)
    expect(full.container.querySelector('[data-prim="tx"]')!.textContent).toBe('abcdefghij')
  })

  it.each(STREAM_NAMES)('draws every primitive of the %s lesson', (name) => {
    const steps = stepsOf(name)
    const { container } = render(<Board state={finished(steps)} title="t" />)
    const expected = steps.flatMap((s) => s.draw).filter((p) => p.type !== 'erase')
    expect(drawnIds(container)).toHaveLength(expected.length)
    expect(container.querySelectorAll('[data-drawn="false"]')).toHaveLength(0)
  })

  it('puts the mascot at the pen while drawing and in its corner when done', () => {
    const steps = [step([{ id: 'ln', type: 'line', x1: 0, y1: 500, x2: 700, y2: 500 }])]
    const drawing = render(<Board state={playing(steps, 0.5)} title="t" />)
    const mascot = drawing.getByTestId('mascot')
    expect(mascot.getAttribute('data-state')).toBe('drawing')
    expect(mascot.style.transform).toContain('translate(350px, 500px)')
    expect(mascot.querySelector('g[transform^="translate(0"]')).toBeNull() // body above the pen
    drawing.unmount()

    const done = render(<Board state={finished(steps)} title="t" />)
    expect(done.getByTestId('mascot').style.transform).toContain('translate(1440px, 975px)')
  })

  it('puts the mascot body below the pen near the top edge, so it stays visible', () => {
    const steps = [step([{ id: 'ln', type: 'line', x1: 0, y1: 60, x2: 700, y2: 60 }])]
    const { getByTestId } = render(<Board state={playing(steps, 0.5)} title="t" />)
    expect(getByTestId('mascot').querySelector('g[transform^="translate(0"]')).not.toBeNull()
  })
})

describe('Scribbly', () => {
  it.each(MASCOT_STATES)('renders the %s state', (state) => {
    const { getByTestId } = render(
      <svg>
        <Scribbly state={state} x={10} y={20} still />
      </svg>,
    )
    expect(getByTestId('mascot').getAttribute('data-state')).toBe(state)
  })

  it('opens its mouth with the narration level', () => {
    const mouth = (level: number) => {
      const { container, unmount } = render(
        <svg>
          <Scribbly state="talking" x={0} y={0} mouth={level} still />
        </svg>,
      )
      const filled = container.querySelector('path[fill="currentColor"]')
      unmount()
      return filled
    }
    expect(mouth(0)).toBeNull()
    expect(mouth(0.8)).not.toBeNull()
  })
})
