// Hand-drawn SVG paths for stroke primitives, made with rough.js.
// Each primitive gets a fixed seed from its id, so its wobble never changes between frames.
// Paths are split into single subpaths, drawn one after another in order.

import rough from 'roughjs'
import type { Options } from 'roughjs/bin/core'
import type { Primitive, XY } from '../lesson/types'
import { HEAD, dist, loopAround, rectPoints, type Box } from './geometry'

export interface Stroke {
  d: string
  /** Approximate length; strokes of one primitive share its progress by length. */
  length: number
  dashed: boolean
}

const generator = rough.generator()
const BASE: Options = {
  roughness: 0.9,
  bowing: 0.7,
  disableMultiStroke: true,
  preserveVertices: true,
  fixedDecimalPlaceDigits: 1,
}

export function seedFor(id: string): number {
  let h = 2166136261
  for (const c of id) h = Math.imul(h ^ c.codePointAt(0)!, 16777619)
  return (h >>> 0) % 2147483646 || 1
}

export function splitSubpaths(d: string): string[] {
  return d
    .split(/(?=M)/)
    .map((s) => s.trim())
    .filter((s) => /[LCQ]/.test(s))
}

/** Sum of distances between the numbers of a path read as points; fine as a weight. */
export function approxLength(d: string): number {
  const nums = (d.match(/-?\d*\.?\d+(?:e-?\d+)?/g) ?? []).map(Number)
  let total = 0
  for (let i = 2; i + 1 < nums.length; i += 2) {
    total += Math.hypot(nums[i] - nums[i - 2], nums[i + 1] - nums[i - 1])
  }
  return Math.max(total, 1)
}

function toStrokes(drawable: ReturnType<typeof generator.line>, dashed: boolean): Stroke[] {
  return generator
    .toPaths(drawable)
    .flatMap((p) => splitSubpaths(p.d))
    .map((d) => ({ d, length: approxLength(d), dashed }))
}

function head(from: XY, to: XY): Stroke {
  const angle = Math.atan2(to[1] - from[1], to[0] - from[0])
  const wing = (a: number): XY => [to[0] - HEAD * Math.cos(a), to[1] - HEAD * Math.sin(a)]
  const [a, b] = [wing(angle - 0.45), wing(angle + 0.45)]
  const f = (p: XY) => `${p[0].toFixed(1)} ${p[1].toFixed(1)}`
  return { d: `M${f(a)} L${f(to)} L${f(b)}`, length: 2 * HEAD, dashed: false }
}

function arrow(from: XY, to: XY, seed: number, dashed = false): Stroke[] {
  const shaft = generator.line(from[0], from[1], to[0], to[1], { ...BASE, seed })
  return dist(from, to) < 1 ? [] : [...toStrokes(shaft, dashed), head(from, to)]
}

function mulberry32(seed: number): () => number {
  let a = seed | 0
  return () => {
    a = (a + 0x6d2b79f5) | 0
    let t = Math.imul(a ^ (a >>> 15), 1 | a)
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296
  }
}

/** A loose, slightly overlapping loop, like a teacher circling something. */
export function loopPath(box: Box, seed: number): string {
  const { cx, cy, rx, ry } = loopAround(box)
  const random = mulberry32(seed)
  const points: string[] = []
  const turns = 2 * Math.PI * 1.15
  for (let a = 0; a <= turns; a += 0.15) {
    const wobble = 1 + (random() - 0.5) * 0.06 + (a / turns) * 0.05
    const angle = -Math.PI / 2 + a
    const x = cx + rx * wobble * Math.cos(angle)
    const y = cy + ry * wobble * Math.sin(angle)
    points.push(`${points.length ? 'L' : 'M'}${x.toFixed(1)} ${y.toFixed(1)}`)
  }
  return points.join(' ')
}

/** Strokes for a primitive; [] for primitives drawn as text, dots or not at all. */
export function strokesFor(prim: Primitive, target: Box | null = null): Stroke[] {
  const o: Options = { ...BASE, seed: seedFor(prim.id) }
  const dashed = 'dashed' in prim && prim.dashed === true
  switch (prim.type) {
    case 'line':
      return toStrokes(generator.line(prim.x1, prim.y1, prim.x2, prim.y2, o), dashed)
    case 'arrow':
      return arrow([prim.x1, prim.y1], [prim.x2, prim.y2], o.seed!, dashed)
    case 'vector':
      return arrow(prim.from, prim.to, o.seed!)
    case 'circle':
      return toStrokes(generator.circle(prim.cx, prim.cy, 2 * prim.r, o), dashed)
    case 'ellipse':
      return toStrokes(generator.ellipse(prim.cx, prim.cy, 2 * prim.rx, 2 * prim.ry, o), dashed)
    case 'rect':
      return toStrokes(generator.linearPath(rectPoints(prim.x, prim.y, prim.w, prim.h), o), dashed)
    case 'polyline': {
      const points = prim.closed ? [...prim.points, prim.points[0]] : prim.points
      return toStrokes(generator.linearPath(points, o), false)
    }
    case 'curve': {
      const shape = prim.points.length < 3 ? generator.linearPath : generator.curve
      return toStrokes(shape.call(generator, prim.points, o), false)
    }
    case 'axes': {
      const origin: XY = [prim.x, prim.y + prim.h]
      return [
        ...arrow(origin, [prim.x + prim.w, prim.y + prim.h], o.seed!),
        ...arrow(origin, [prim.x, prim.y], o.seed! + 1),
      ]
    }
    case 'highlight':
    case 'mark_wrong': {
      if (!target) return []
      const d = loopPath(target, o.seed!)
      return [{ d, length: approxLength(d), dashed: false }]
    }
    default:
      return []
  }
}

/** How much of each stroke is drawn when `progress` of the whole primitive is drawn. */
export function strokeProgress(strokes: Stroke[], progress: number): number[] {
  const total = strokes.reduce((sum, s) => sum + s.length, 0)
  let left = progress * total
  return strokes.map((s) => {
    const k = Math.min(1, Math.max(0, left / s.length))
    left -= s.length
    return k
  })
}
