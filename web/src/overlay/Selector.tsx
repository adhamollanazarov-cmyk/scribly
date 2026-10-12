import { useEffect, useRef, useState, type PointerEvent } from 'react'
import { t } from '../i18n'
import { dragRect, isUsableRegion, type Point, type Rect } from './geometry'

/** Dims the screen; the user drags over what should be explained. Esc or right-click cancels. */
export function Selector({ onDone }: { onDone: (region: Rect | null) => void }) {
  const start = useRef<Point | null>(null)
  const [rect, setRect] = useState<Rect | null>(null)

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onDone(null)
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [onDone])

  const screen = () => ({ w: window.innerWidth, h: window.innerHeight })
  const at = (e: PointerEvent): Point => [e.clientX, e.clientY]

  const down = (e: PointerEvent<HTMLDivElement>) => {
    if (e.button !== 0) return
    e.currentTarget.setPointerCapture?.(e.pointerId)
    start.current = at(e)
    setRect(dragRect(at(e), at(e), screen()))
  }
  const move = (e: PointerEvent) => {
    if (start.current) setRect(dragRect(start.current, at(e), screen()))
  }
  const up = (e: PointerEvent) => {
    if (!start.current) return
    const region = dragRect(start.current, at(e), screen())
    start.current = null
    if (isUsableRegion(region)) onDone(region)
    else setRect(null)
  }

  return (
    <div
      className="selector"
      data-testid="selector"
      data-dragging={rect ? 'true' : 'false'}
      onPointerDown={down}
      onPointerMove={move}
      onPointerUp={up}
      onContextMenu={(e) => {
        e.preventDefault()
        onDone(null)
      }}
    >
      {rect ? (
        <div
          className="selector-rect"
          data-testid="selector-rect"
          style={{ left: rect.x, top: rect.y, width: rect.w, height: rect.h }}
        />
      ) : (
        <p className="selector-hint">{t('overlay.hint')}</p>
      )}
    </div>
  )
}
