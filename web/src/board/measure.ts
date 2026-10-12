// Measurements use actual browser fonts and full content, independent of stroke reveal.
// No capture, disk output or external service. jsdom returns zero boxes: use pure fallbacks there.
import type { Primitive } from '../lesson/types'
import { MATH_SIZE, SYMBOL_SIZE, TEXT_SIZE, symbolLine, type Box } from './geometry'
import { handRuns } from './handRuns'
import { renderLatex } from './katex'

const SVG = 'http://www.w3.org/2000/svg'
const handCache = new Map<string, Box | null>()
export const clearMeasurements = () => handCache.clear()

function handContent(element: Element, text: string, svg = false) {
  for (const run of handRuns(text)) {
    const child = svg
      ? document.createElementNS(SVG, 'tspan')
      : document.createElement(
          run.position === 'normal' ? 'span' : run.position === 'super' ? 'sup' : 'sub',
        )
    if (svg && run.position !== 'normal') {
      child.setAttribute('baseline-shift', run.position)
      child.setAttribute('font-size', '70%')
    }
    child.textContent = run.text
    element.append(child)
  }
}

export function measureHand(text: string, size: number): Box | null {
  const key = `${size}:${text}`
  if (handCache.has(key)) return handCache.get(key) ?? null
  const host = document.createElementNS(SVG, 'svg')
  host.style.cssText =
    'position:fixed;left:-10000px;top:0;overflow:visible;visibility:hidden;pointer-events:none'
  const label = document.createElementNS(SVG, 'text')
  label.setAttribute('font-size', String(size))
  label.setAttribute('class', 'hand')
  handContent(label, text, true)
  host.append(label)
  document.body.append(host)
  try {
    const box = label.getBBox?.()
    const chars = label.getNumberOfChars?.() ?? 0
    const advances = Array.from({ length: chars + 1 }, (_, n) =>
      n ? label.getSubStringLength(0, n) : 0,
    )
    const measured = box?.width
      ? { x: box.x, y: box.y, w: box.width, h: box.height, advances }
      : null
    handCache.set(key, measured)
    return measured
  } finally {
    host.remove()
  }
}

export function measurePrimitive(prim: Primitive): Box | null {
  if (prim.type === 'text') {
    const b = measureHand(prim.text, prim.size ?? TEXT_SIZE)
    return b ? { ...b, x: prim.x + b.x, y: prim.y + b.y } : null
  }
  if (prim.type !== 'math' && prim.type !== 'symbol') return null
  const size = prim.type === 'math' ? (prim.size ?? MATH_SIZE) : SYMBOL_SIZE
  const host = document.createElement('div')
  host.style.cssText = `position:fixed;left:-10000px;top:0;width:max-content;white-space:nowrap;visibility:hidden;pointer-events:none;font-size:${size}px`
  const marker = document.createElement('span')
  marker.className = 'baseline-marker'
  host.append(marker)
  const formula = document.createElement('span')
  formula.innerHTML = renderLatex(prim.type === 'math' ? prim.latex : prim.symbol)
  host.append(formula)
  if (prim.type === 'symbol') {
    const meaning = document.createElement('span')
    meaning.className = 'hand symbol-meaning'
    handContent(meaning, symbolLine(prim))
    host.append(meaning)
  }
  document.body.append(host)
  try {
    const b = host.getBoundingClientRect()
    const baseline = marker.getBoundingClientRect().top - b.top
    return b.width ? { x: prim.x, y: prim.y - baseline, w: b.width, h: b.height } : null
  } finally {
    host.remove()
  }
}
