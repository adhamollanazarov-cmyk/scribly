import { useEffect } from 'react'
import type { OverlayBridge } from './bridge'

/**
 * The overlay window ignores the mouse (clicks reach the app below) except over elements
 * marked `data-interactive`. Electron still forwards mouse moves, so we can tell when the
 * pointer enters one of them and ask main to take clicks again.
 */
export function useClickThrough(bridge: OverlayBridge) {
  useEffect(() => {
    let interactive = false
    const update = (next: boolean) => {
      if (next === interactive) return
      interactive = next
      bridge.setInteractive(next)
    }
    const onMove = (e: MouseEvent) => {
      update(e.target instanceof Element && e.target.closest('[data-interactive]') !== null)
    }
    const onLeave = () => update(false)
    document.addEventListener('mousemove', onMove)
    document.addEventListener('mouseleave', onLeave)
    return () => {
      document.removeEventListener('mousemove', onMove)
      document.removeEventListener('mouseleave', onLeave)
      update(false)
    }
  }, [bridge])
}
