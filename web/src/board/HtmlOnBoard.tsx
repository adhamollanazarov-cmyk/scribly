import { useLayoutEffect, useRef, type CSSProperties, type ReactNode } from 'react'

const ROOM = 4 // the foreignObject reaches this many font sizes above and below the baseline

/**
 * HTML content (KaTeX, mixed text) placed on the SVG board with its text baseline at
 * (x, y), like SVG <text>. A zero-size inline-block sits on the baseline; we measure it
 * and move the content up by that much. `top` is set here only, never by React.
 * `reveal` (0–1) wipes the content in from the left, like writing.
 */
export function HtmlOnBoard(props: {
  x: number
  y: number
  size: number
  reveal: number
  color: string
  children: ReactNode
}) {
  const { x, y, size, reveal, color, children } = props
  const box = useRef<HTMLDivElement>(null)
  const marker = useRef<HTMLSpanElement>(null)
  const room = ROOM * size

  useLayoutEffect(() => {
    if (!box.current) return
    const baseline = marker.current?.offsetTop || size // jsdom has no layout
    box.current.style.top = `${room - baseline}px`
    const align = () => {
      if (box.current) box.current.style.top = `${room - (marker.current?.offsetTop || size)}px`
    }
    const observer = typeof ResizeObserver === 'undefined' ? null : new ResizeObserver(align)
    observer?.observe(box.current)
    return () => observer?.disconnect()
  }, [children, size, room])

  const style: CSSProperties = {
    position: 'absolute',
    left: 0,
    fontSize: size,
    color,
    whiteSpace: 'nowrap',
    width: 'max-content',
    clipPath: reveal >= 1 ? undefined : `inset(-50% ${(1 - reveal) * 100}% -50% 0)`,
  }
  return (
    <foreignObject
      x={x}
      y={y - room}
      width={Math.max(200, 1600 - x)}
      height={2 * room}
      style={{ overflow: 'visible', pointerEvents: 'none' }}
    >
      <div ref={box} style={style}>
        <span ref={marker} className="baseline-marker" />
        {children}
      </div>
    </foreignObject>
  )
}
