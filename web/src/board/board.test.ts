import { describe, expect, it } from 'vitest'
import type { Primitive } from '../lesson/types'
import { stepsOf } from '../test/fakes'
import { boardFrame } from './frame'
import { latexGlyphs, naturalDuration, penAt, viewBoxFor } from './geometry'
import { buildSchedule, estimateNarration, progressAt, stepEnd } from './schedule'
import { seedFor, splitSubpaths, strokeProgress, strokesFor } from './strokes'

const line = (id: string, at?: number): Primitive => ({
  id,
  type: 'line',
  x1: 0,
  y1: 0,
  x2: 700,
  y2: 0,
  at,
})

describe('schedule', () => {
  it('spreads primitives without `at` evenly and keeps one pen', () => {
    const s = buildSchedule([line('a'), line('b'), line('c'), line('d')], 8)
    expect(s.slots.map((x) => x.start)).toEqual([0, 2, 4, 6])
    expect(s.slots[0].end).toBeCloseTo(1) // 700 px at 700 px/s
  })

  it('draws primitives sharing one `at` one after another', () => {
    const s = buildSchedule([line('a', 0.1), line('b', 0.1), line('c', 0.1)], 10)
    expect(s.slots[1].start).toBeCloseTo(s.slots[0].end)
    expect(s.slots[2].start).toBeCloseTo(s.slots[1].end)
  })

  it('shrinks strokes so the drawing ends with the narration', () => {
    const prims = Array.from({ length: 12 }, (_, i) => line(`l${i}`, 0.15))
    const s = buildSchedule(prims, 3)
    expect(s.drawEnd).toBeLessThanOrEqual(3)
    expect(s.drawEnd).toBeGreaterThan(2.5)
    expect(stepEnd(s)).toBe(3)
  })

  it('draws back to back at the natural pace when there is no narration', () => {
    const s = buildSchedule([line('a'), line('b')], 0)
    expect(s.slots).toEqual([
      { start: 0, end: 1 },
      { start: 1, end: 2 },
    ])
  })

  it('reports progress inside a slot', () => {
    expect(progressAt({ start: 1, end: 3 }, 2)).toBe(0.5)
    expect(progressAt({ start: 1, end: 3 }, 0)).toBe(0)
    expect(progressAt({ start: 1, end: 1 }, 1)).toBe(1)
  })

  it('estimates narration from word count', () => {
    expect(estimateNarration('one two three')).toBeGreaterThan(1)
  })

  it.each(['gauss_law', 'circ_series', 'force_vector'])('fits every step of %s', (name) => {
    for (const step of stepsOf(name)) {
      const length = estimateNarration(step.say)
      const s = buildSchedule(step.draw, length)
      expect(s.drawEnd).toBeLessThanOrEqual(length)
    }
  })
})

describe('frame', () => {
  const box: Primitive = { id: 'b', type: 'rect', x: 100, y: 100, w: 50, h: 50, group: 'g' }
  const hl: Primitive = { id: 'h', type: 'highlight', target_id: 'g' }
  const erase: Primitive = { id: 'e', type: 'erase', target_id: 'b' }

  it('draws earlier steps fully and the current one by its schedule', () => {
    const steps = [{ draw: [box] }, { draw: [line('a'), line('b')] }]
    const schedule = buildSchedule(steps[1].draw, 4)
    const frame = boardFrame(steps, 1, { schedule, t: 0.5 })

    expect(frame.prims.map((d) => [d.prim.id, d.progress])).toEqual([
      ['b', 1],
      ['a', 0.5],
    ])
    expect(frame.pen).toEqual([350, 0])
  })

  it('finds highlight targets by group and fades erased primitives', () => {
    const steps = [{ draw: [box] }, { draw: [hl, erase] }]
    const frame = boardFrame(steps, 2, null)
    const byId = Object.fromEntries(frame.prims.map((d) => [d.prim.id, d]))

    expect(byId.h.target).toEqual({ x: 100, y: 100, w: 50, h: 50 })
    expect(byId.b.opacity).toBe(0)
  })

  it('has no pen when nothing is being drawn', () => {
    expect(boardFrame([{ draw: [box] }], 1, null).pen).toBeNull()
  })
})

describe('geometry', () => {
  it('follows a circle from the top, clockwise on screen', () => {
    const c: Primitive = { id: 'c', type: 'circle', cx: 0, cy: 0, r: 10 }
    expect(penAt(c, 0)![1]).toBeCloseTo(-10)
    expect(penAt(c, 0.25)![0]).toBeCloseTo(10)
  })

  it('walks a rectangle along its edges', () => {
    const r: Primitive = { id: 'r', type: 'rect', x: 0, y: 0, w: 10, h: 10 }
    expect(penAt(r, 0.5)).toEqual([10, 10])
  })

  it('counts visible glyphs in LaTeX', () => {
    expect(latexGlyphs('\\Phi')).toBe(1)
    expect(latexGlyphs('\\dfrac{Q}{\\varepsilon_0}')).toBeLessThan(4)
  })

  it('does not evaluate raw plots in the browser (the server sends curves)', () => {
    const plot: Primitive = {
      id: 'p',
      type: 'plot',
      axes_id: 'a',
      expr: 'x',
      x_min: 0,
      x_max: 1,
      y_min: 0,
      y_max: 1,
    }
    expect(naturalDuration(plot)).toBe(0)
  })

  it('turns a focus rect into a 16:10 view', () => {
    expect(viewBoxFor(null)).toEqual({ x: 0, y: 0, w: 1600, h: 1000 })
    expect(viewBoxFor({ x: 0, y: 0, w: 800, h: 800 })).toEqual({ x: -240, y: 0, w: 1280, h: 800 })
  })
})

describe('strokes', () => {
  it('is the same every time for the same id', () => {
    expect(strokesFor(line('a'))).toEqual(strokesFor(line('a')))
    expect(seedFor('a')).not.toBe(seedFor('b'))
  })

  it('splits paths into subpaths that each draw something', () => {
    expect(splitSubpaths('M0 0 L1 1 M2 2 C3 3 4 4 5 5 M9 9')).toEqual([
      'M0 0 L1 1',
      'M2 2 C3 3 4 4 5 5',
    ])
  })

  it('draws an arrow as a shaft and then its head', () => {
    const arrow: Primitive = { id: 'a', type: 'arrow', x1: 0, y1: 0, x2: 100, y2: 0 }
    const strokes = strokesFor(arrow)
    expect(strokes.length).toBeGreaterThanOrEqual(2)
    expect(strokeProgress(strokes, 0.5).at(-1)).toBe(0) // head comes last
    expect(strokeProgress(strokes, 1).every((k) => k === 1)).toBe(true)
  })

  it('keeps the dash flag for dashed outlines only', () => {
    const c: Primitive = { id: 'c', type: 'circle', cx: 0, cy: 0, r: 50, dashed: true }
    expect(strokesFor(c).every((s) => s.dashed)).toBe(true)
  })

  it('needs a target to circle', () => {
    const hl: Primitive = { id: 'h', type: 'highlight', target_id: 'x' }
    expect(strokesFor(hl)).toEqual([])
    expect(strokesFor(hl, { x: 0, y: 0, w: 10, h: 10 })).toHaveLength(1)
  })
})
