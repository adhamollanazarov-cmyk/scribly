// Pure geometry for primitives: sizes, bounding boxes, stroke lengths and where the pen is.
// Text estimates are fallbacks before browser font measurements are available.

import type { Primitive, Rect, XY } from '../lesson/types'

export const CANVAS = { w: 1600, h: 1000 }
export const TEXT_SIZE = 36
export const MATH_SIZE = 36
export const SYMBOL_SIZE = 32
export const HEAD = 16 // arrowhead side length
const HAND_CHAR = 0.34 // Caveat average glyph width, in em (measured in Chromium)
const KATEX_SCALE = 1.21 // KaTeX renders at 1.21em of its container
const MATH_CHAR = 0.55

export interface Box {
  x: number
  y: number
  w: number
  h: number
  advances?: number[]
}

export const dist = (a: XY, b: XY) => Math.hypot(b[0] - a[0], b[1] - a[1])
const lerp = (a: XY, b: XY, k: number): XY => [a[0] + (b[0] - a[0]) * k, a[1] + (b[1] - a[1]) * k]
const clamp = (v: number, lo: number, hi: number) => Math.min(hi, Math.max(lo, v))

export function textWidth(text: string, size: number): number {
  return [...text].length * size * HAND_CHAR
}

/** Rough count of visible glyphs in a LaTeX string. */
export function latexGlyphs(latex: string): number {
  const visible = latex
    .replace(/\\(?:mathrm|text|mathbf|operatorname|left|right|dfrac|tfrac|frac|vec|hat|bar)\b/g, '')
    .replace(/\\[,;:! ]|\\quad|\\qquad/g, ' ')
    .replace(/\\[a-zA-Z]+/g, 'x')
    .replace(/[{}_^\\]/g, '')
  const fracs = (latex.match(/\\[dt]?frac/g) ?? []).length
  return Math.max(1, visible.length - fracs * 2)
}

export function mathWidth(latex: string, size: number): number {
  return latexGlyphs(latex) * size * KATEX_SCALE * MATH_CHAR
}

export function symbolLine(prim: { meaning: string; unit?: string | null }): string {
  return ` — ${prim.meaning}${prim.unit ? ` (${prim.unit})` : ''}`
}

export function boxOf(prim: Primitive): Box | null {
  switch (prim.type) {
    case 'point': {
      const r = prim.r ?? 6
      return { x: prim.x - r, y: prim.y - r, w: 2 * r, h: 2 * r }
    }
    case 'line':
    case 'arrow':
      return boxOfPoints([
        [prim.x1, prim.y1],
        [prim.x2, prim.y2],
      ])
    case 'vector':
      return boxOfPoints([prim.from, prim.to])
    case 'circle':
      return { x: prim.cx - prim.r, y: prim.cy - prim.r, w: 2 * prim.r, h: 2 * prim.r }
    case 'ellipse':
      return { x: prim.cx - prim.rx, y: prim.cy - prim.ry, w: 2 * prim.rx, h: 2 * prim.ry }
    case 'rect':
    case 'axes':
      return { x: prim.x, y: prim.y, w: prim.w, h: prim.h }
    case 'polyline':
    case 'curve':
      return boxOfPoints(prim.points)
    case 'text': {
      const size = prim.size ?? TEXT_SIZE
      return { x: prim.x, y: prim.y - size * 0.8, w: textWidth(prim.text, size), h: size }
    }
    case 'math': {
      const size = prim.size ?? MATH_SIZE
      const h = size * KATEX_SCALE
      return { x: prim.x, y: prim.y - h * 0.9, w: mathWidth(prim.latex, size), h: h * 1.2 }
    }
    case 'symbol': {
      const w = mathWidth(prim.symbol, SYMBOL_SIZE) + textWidth(symbolLine(prim), SYMBOL_SIZE)
      return { x: prim.x, y: prim.y - SYMBOL_SIZE * 0.9, w, h: SYMBOL_SIZE * 1.2 }
    }
    default:
      return null
  }
}

export function boxOfPoints(points: XY[]): Box {
  const xs = points.map((p) => p[0])
  const ys = points.map((p) => p[1])
  const x = Math.min(...xs)
  const y = Math.min(...ys)
  return { x, y, w: Math.max(...xs) - x, h: Math.max(...ys) - y }
}

export function unionBox(boxes: Box[]): Box | null {
  if (!boxes.length) return null
  const x = Math.min(...boxes.map((b) => b.x))
  const y = Math.min(...boxes.map((b) => b.y))
  const right = Math.max(...boxes.map((b) => b.x + b.w))
  const bottom = Math.max(...boxes.map((b) => b.y + b.h))
  return { x, y, w: right - x, h: bottom - y }
}

/** The loose loop drawn around a highlight or mark_wrong target. */
export function loopAround(box: Box): { cx: number; cy: number; rx: number; ry: number } {
  return {
    cx: box.x + box.w / 2,
    cy: box.y + box.h / 2,
    rx: box.w / 2 + 22,
    ry: box.h / 2 + 18,
  }
}

function polylineLength(points: XY[]): number {
  let total = 0
  for (let i = 1; i < points.length; i++) total += dist(points[i - 1], points[i])
  return total
}

function alongPolyline(points: XY[], k: number): XY {
  const total = polylineLength(points)
  let left = clamp(k, 0, 1) * total
  for (let i = 1; i < points.length; i++) {
    const seg = dist(points[i - 1], points[i])
    if (left <= seg || i === points.length - 1) {
      return lerp(points[i - 1], points[i], seg ? clamp(left / seg, 0, 1) : 1)
    }
    left -= seg
  }
  return points[0]
}

function ellipseAt(cx: number, cy: number, rx: number, ry: number, k: number): XY {
  const a = -Math.PI / 2 + k * 2 * Math.PI // rough.js starts near the top, clockwise on screen
  return [cx + rx * Math.cos(a), cy + ry * Math.sin(a)]
}

export function rectPoints(x: number, y: number, w: number, h: number): XY[] {
  return [
    [x, y],
    [x + w, y],
    [x + w, y + h],
    [x, y + h],
    [x, y],
  ]
}

function axesPoints(prim: { x: number; y: number; w: number; h: number }): XY[] {
  const origin: XY = [prim.x, prim.y + prim.h]
  return [[prim.x + prim.w, prim.y + prim.h], origin, [prim.x, prim.y]]
}

/** Where the pen tip is when `k` (0–1) of the primitive is drawn; null if nothing is drawn. */
export function penAt(
  prim: Primitive,
  k: number,
  target?: Box | null,
  measured?: Box | null,
): XY | null {
  switch (prim.type) {
    case 'point':
      return [prim.x, prim.y]
    case 'line':
    case 'arrow':
      return lerp([prim.x1, prim.y1], [prim.x2, prim.y2], k)
    case 'vector':
      return lerp(prim.from, prim.to, k)
    case 'circle':
      return ellipseAt(prim.cx, prim.cy, prim.r, prim.r, k)
    case 'ellipse':
      return ellipseAt(prim.cx, prim.cy, prim.rx, prim.ry, k)
    case 'rect':
      return alongPolyline(rectPoints(prim.x, prim.y, prim.w, prim.h), k)
    case 'polyline':
      return alongPolyline(prim.closed ? [...prim.points, prim.points[0]] : prim.points, k)
    case 'curve':
      return alongPolyline(prim.points, k)
    case 'axes':
      return alongPolyline(axesPoints(prim), k)
    case 'text': {
      const size = prim.size ?? TEXT_SIZE
      if (measured?.advances) {
        const a = measured.advances
        return [prim.x + a[Math.ceil(clamp(k, 0, 1) * (a.length - 1))], prim.y]
      }
      return [prim.x + (measured?.w ?? textWidth(prim.text, size)) * k, prim.y]
    }
    case 'math':
    case 'symbol': {
      const box = measured ?? boxOf(prim)
      return box ? [box.x + box.w * k, prim.y] : null
    }
    case 'highlight':
    case 'mark_wrong': {
      if (!target) return null
      const { cx, cy, rx, ry } = loopAround(target)
      return ellipseAt(cx, cy, rx, ry, Math.min(k * 1.15, 1.15))
    }
    default:
      return null
  }
}

/** Seconds of narration time a primitive takes to draw at its natural pace. */
export function naturalDuration(prim: Primitive): number {
  const PEN = 700 // px per second
  switch (prim.type) {
    case 'point':
      return 0.25
    case 'line':
    case 'arrow':
      return clamp(dist([prim.x1, prim.y1], [prim.x2, prim.y2]) / PEN, 0.25, 1.4)
    case 'vector':
      return clamp(dist(prim.from, prim.to) / PEN + 0.3, 0.4, 1.6)
    case 'circle':
      return clamp((2 * Math.PI * prim.r) / PEN, 0.4, 1.8)
    case 'ellipse':
      return clamp((Math.PI * (prim.rx + prim.ry)) / PEN, 0.4, 1.8)
    case 'rect':
      return clamp((2 * (prim.w + prim.h)) / PEN, 0.3, 1.6)
    case 'polyline':
    case 'curve':
      return clamp(polylineLength(prim.points) / PEN, 0.3, 1.8)
    case 'axes':
      return clamp((prim.w + prim.h) / PEN + 0.4, 0.6, 1.8)
    case 'text':
      return clamp([...prim.text].length * 0.06, 0.3, 2.2)
    case 'math':
      return clamp(latexGlyphs(prim.latex) * 0.07, 0.5, 2.2)
    case 'symbol':
      return clamp((latexGlyphs(prim.symbol) + prim.meaning.length) * 0.04, 0.6, 1.8)
    case 'highlight':
      return 0.6
    case 'mark_wrong':
      return 1.2
    case 'erase':
      return 0.4
    default:
      return 0 // plot and template are not drawn
  }
}

/** The focus rect as a viewBox that keeps the 16:10 board ratio. */
export function viewBoxFor(focus: Rect | null | undefined): Box {
  if (!focus) return { x: 0, y: 0, ...CANVAS }
  const ratio = CANVAS.w / CANVAS.h
  let { w, h } = focus
  if (w / h > ratio) h = w / ratio
  else w = h * ratio
  return { x: focus.x + (focus.w - w) / 2, y: focus.y + (focus.h - h) / 2, w, h }
}
