import { memo, useId, useMemo } from 'react'
import type { Color, Primitive, XY } from '../lesson/types'
import type { DrawnPrim } from './frame'
import { MATH_SIZE, SYMBOL_SIZE, TEXT_SIZE, symbolLine, textWidth, type Box } from './geometry'
import { HtmlOnBoard } from './HtmlOnBoard'
import { renderLatex } from './katex'
import { strokeProgress, strokesFor, type Stroke } from './strokes'

const DEFAULT_COLOR: Partial<Record<Primitive['type'], Color>> = {
  highlight: 'highlight',
  mark_wrong: 'wrong',
}
const LABEL_SIZE = 30
// erase draws nothing itself; plot needs server sampling (use axes_plot); templates arrive expanded
const NOT_DRAWN = new Set<Primitive['type']>(['erase', 'plot', 'template'])

const colorVar = (prim: Primitive) => `var(--c-${prim.color ?? DEFAULT_COLOR[prim.type] ?? 'ink'})`

const clamp01 = (v: number) => Math.min(1, Math.max(0, v))
const typed = (text: string, k: number) => [...text].slice(0, Math.ceil(k * [...text].length))

function StrokePath({ stroke, k, color, width }: StrokeProps) {
  const maskId = useId()
  if (k <= 0) return null
  const reveal = { pathLength: 1, strokeDasharray: '1 1', strokeDashoffset: 1 - k }
  const common = {
    d: stroke.d,
    fill: 'none',
    strokeWidth: width,
    strokeLinecap: 'round' as const,
    strokeLinejoin: 'round' as const,
  }
  if (!stroke.dashed) {
    return <path {...common} stroke={color} {...(k < 1 ? reveal : {})} />
  }
  // Dashed: its own dash pattern, revealed through a growing mask.
  return (
    <>
      {k < 1 && (
        <mask id={maskId} maskUnits="userSpaceOnUse" x={-2000} y={-2000} width={6000} height={5000}>
          <path {...common} stroke="white" strokeWidth={width + 8} {...reveal} />
        </mask>
      )}
      <path
        {...common}
        stroke={color}
        strokeDasharray="14 10"
        mask={k < 1 ? `url(#${maskId})` : undefined}
      />
    </>
  )
}

interface StrokeProps {
  stroke: Stroke
  k: number
  color: string
  width: number
}

function strokeWidth(prim: Primitive): number {
  if (prim.color === 'field') return 2.6
  if (prim.type === 'highlight' || prim.type === 'mark_wrong') return 3.2
  return 3.4
}

/** Where a primitive's `label` goes, as a text baseline start. */
function labelAnchor(prim: Primitive, label: string): XY | null {
  const w = textWidth(label, LABEL_SIZE)
  switch (prim.type) {
    case 'circle':
      return [prim.cx + prim.r * 0.72 + 10, prim.cy - prim.r * 0.72 - 10]
    case 'ellipse':
      return [prim.cx + prim.rx * 0.72 + 10, prim.cy - prim.ry * 0.72 - 10]
    case 'rect':
      return [prim.x + prim.w / 2 - w / 2, prim.y - 12]
    case 'point':
      return [prim.x + (prim.r ?? 6) + 8, prim.y - (prim.r ?? 6) - 6]
    case 'line':
    case 'arrow': {
      const [mx, my] = [(prim.x1 + prim.x2) / 2, (prim.y1 + prim.y2) / 2]
      const vertical = Math.abs(prim.x2 - prim.x1) < Math.abs(prim.y2 - prim.y1)
      return vertical ? [mx + 14, my + 10] : [mx - w / 2, my - 14]
    }
    case 'polyline':
    case 'curve': {
      const [x, y] = prim.points[prim.points.length - 1]
      return [x + 10, y - 10]
    }
    default:
      return null
  }
}

function vectorNameAnchor(from: XY, to: XY): XY {
  const len = Math.hypot(to[0] - from[0], to[1] - from[1]) || 1
  const [ux, uy] = [(to[0] - from[0]) / len, (to[1] - from[1]) / len]
  // Beside the tip, on the upper side of the arrow.
  const [nx, ny] = uy > 0 || (uy === 0 && ux < 0) ? [uy, -ux] : [-uy, ux]
  return [to[0] + ux * 8 + nx * 26 - (ux < 0 ? 40 : 0), to[1] + uy * 8 + ny * 26 + 8]
}

function HandText(props: {
  x: number
  y: number
  text: string
  k: number
  size: number
  color: string
}) {
  const { x, y, text, k, size, color } = props
  if (k <= 0) return null
  return (
    <text x={x} y={y} fontSize={size} fill={color} className="hand">
      {typed(text, k).join('')}
    </text>
  )
}

function Body({ drawn, color }: { drawn: DrawnPrim; color: string }) {
  const { prim, progress } = drawn
  switch (prim.type) {
    case 'point':
      return (
        <circle cx={prim.x} cy={prim.y} r={(prim.r ?? 6) * clamp01(progress * 1.5)} fill={color} />
      )
    case 'text': {
      const size = prim.size ?? TEXT_SIZE
      return (
        <HandText x={prim.x} y={prim.y} text={prim.text} k={progress} size={size} color={color} />
      )
    }
    case 'math':
      return (
        <HtmlOnBoard
          x={prim.x}
          y={prim.y}
          size={prim.size ?? MATH_SIZE}
          reveal={progress}
          color={color}
        >
          <span dangerouslySetInnerHTML={{ __html: renderLatex(prim.latex) }} />
        </HtmlOnBoard>
      )
    case 'symbol':
      return (
        <HtmlOnBoard x={prim.x} y={prim.y} size={SYMBOL_SIZE} reveal={progress} color={color}>
          <span dangerouslySetInnerHTML={{ __html: renderLatex(prim.symbol) }} />
          <span className="hand symbol-meaning">{symbolLine(prim)}</span>
        </HtmlOnBoard>
      )
    case 'mark_wrong': {
      if (!drawn.target) return null
      const { x, y, h } = drawn.target
      const k = clamp01((progress - 0.5) / 0.5)
      return (
        <HandText x={x} y={y + h + 52} text={prim.reason} k={k} size={TEXT_SIZE} color={color} />
      )
    }
    default:
      return null
  }
}

function Extras({ drawn, color }: { drawn: DrawnPrim; color: string }) {
  const { prim, progress } = drawn
  if (prim.type === 'vector') {
    const [x, y] = vectorNameAnchor(prim.from, prim.to)
    const k = clamp01((progress - 0.6) / 0.4)
    return <HandText x={x} y={y} text={prim.name} k={k} size={LABEL_SIZE + 4} color={color} />
  }
  if (prim.type === 'axes') {
    const k = clamp01((progress - 0.6) / 0.4)
    const xlabelX = prim.x + prim.w - textWidth(prim.xlabel, LABEL_SIZE)
    const common = { k, size: LABEL_SIZE, color }
    return (
      <>
        <HandText x={xlabelX} y={prim.y + prim.h + 40} text={prim.xlabel} {...common} />
        <HandText x={prim.x + 14} y={prim.y - 8} text={prim.ylabel} {...common} />
      </>
    )
  }
  if (!prim.label) return null
  const anchor = labelAnchor(prim, prim.label)
  if (!anchor) return null
  const k = clamp01((progress - 0.7) / 0.3)
  return (
    <HandText x={anchor[0]} y={anchor[1]} text={prim.label} k={k} size={LABEL_SIZE} color={color} />
  )
}

function PrimViewImpl({ drawn }: { drawn: DrawnPrim }) {
  const { prim, progress, opacity, target } = drawn
  const targetKey = target ? `${target.x},${target.y},${target.w},${target.h}` : ''
  // eslint-disable-next-line react-hooks/exhaustive-deps -- `target` is rebuilt every frame; its key is stable
  const strokes = useMemo(() => strokesFor(prim, target), [prim, targetKey])
  if (opacity <= 0 || NOT_DRAWN.has(prim.type)) return null
  const color = colorVar(prim)
  const width = strokeWidth(prim)
  const ks = strokeProgress(strokes, prim.type === 'mark_wrong' ? progress * 2 : progress)
  return (
    <g
      data-prim={prim.id}
      data-type={prim.type}
      data-drawn={progress >= 1 ? 'true' : 'false'}
      opacity={opacity < 1 ? opacity : undefined}
    >
      {strokes.map((s, i) => (
        <StrokePath key={i} stroke={s} k={ks[i]} color={color} width={width} />
      ))}
      <Body drawn={drawn} color={color} />
      <Extras drawn={drawn} color={color} />
    </g>
  )
}

export const PrimView = memo(PrimViewImpl, (a, b) => {
  const [x, y] = [a.drawn, b.drawn]
  return x.prim === y.prim && x.progress === y.progress && x.opacity === y.opacity && sameBox(x, y)
})

function sameBox(a: DrawnPrim, b: DrawnPrim): boolean {
  const [p, q]: (Box | null)[] = [a.target, b.target]
  return p === q || (!!p && !!q && p.x === q.x && p.y === q.y && p.w === q.w && p.h === q.h)
}
