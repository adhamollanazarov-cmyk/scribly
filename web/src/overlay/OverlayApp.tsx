import { lazy, Suspense, useCallback, useEffect, useState } from 'react'
import type { LessonMode, OverlayBridge } from './bridge'
import { Selector } from './Selector'

const LessonOverlay = lazy(() =>
  import('./LessonOverlay').then((m) => ({ default: m.LessonOverlay })),
)

type View =
  { kind: 'none' } | { kind: 'select' } | { kind: 'lesson'; lesson: LessonMode; n: number }

/** The page inside Electron's transparent window: the region selector, then the lesson. */
export function OverlayApp({ bridge }: { bridge: OverlayBridge }) {
  const [view, setView] = useState<View>({ kind: 'none' })
  const [dismissed, setDismissed] = useState(false)

  useEffect(
    () =>
      bridge.onMode((mode) => {
        if (mode.mode === 'dismiss') return setDismissed(true)
        setDismissed(false)
        setView((v) =>
          mode.mode === 'select'
            ? { kind: 'select' }
            : { kind: 'lesson', lesson: mode, n: v.kind === 'lesson' ? v.n + 1 : 0 },
        )
      }),
    [bridge],
  )

  const select = useCallback(
    (region: Parameters<OverlayBridge['selectRegion']>[0]) => {
      bridge.selectRegion(region)
    },
    [bridge],
  )
  const dismiss = useCallback(() => setDismissed(true), [])

  if (view.kind === 'select') return <Selector onDone={select} />
  if (view.kind !== 'lesson') return null
  return (
    <Suspense fallback={null}>
      <LessonOverlay
        key={view.n}
        lesson={view.lesson}
        bridge={bridge}
        dismissed={dismissed}
        onDismiss={dismiss}
      />
    </Suspense>
  )
}
