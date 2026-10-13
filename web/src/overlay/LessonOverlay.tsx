import { useEffect, useReducer, useState, useSyncExternalStore } from 'react'
import { BoardView } from '../board/Board'
import { useBoardScene, type BoardScene } from '../board/scene'
import { t } from '../i18n'
import { StreamError, streamEvents } from '../lesson/client'
import type { LessonEvent } from '../lesson/types'
import { Scribbly } from '../mascot/Scribbly'
import { LessonPlayer, type Narration, type Ticker } from '../player/engine'
import { BrowserNarration, animationFrameTicker } from '../player/narration'
import { CheckpointCard } from '../ui/CheckpointCard'
import { Subtitles } from '../ui/Subtitles'
import type { LessonMode, OverlayBridge } from './bridge'
import {
  boardPlacement,
  boardToWindow,
  dockRect,
  nearestCorner,
  type Rect,
  type Size,
} from './geometry'
import {
  activityFor,
  APPEAR_MS,
  DISAPPEAR_MS,
  FLY_MS,
  HIDDEN,
  nextMotion,
  poseFor,
  type Motion,
} from './motion'
import { Pill } from './Pill'
import { demoTopicTitle } from './settings'
import { useClickThrough } from './useClickThrough'

const DEMO_HEADER = 'X-Scribbly-Demo'
const DOCK_HEIGHT = 210 // demo notice + two EN lines + two second-language lines + pill
const MASCOT_SCALE = 1.4
const MASCOT_HEADROOM = 130 // window px above the marker tip the body needs
/**
 * Once the lesson has ended by itself (or failed), Scribbly waves goodbye and leaves after
 * this long without pointer movement; closing the window also releases the global Esc.
 */
export const LINGER_MS = 6000

const TIMED: Partial<Record<Motion, [number, 'arrived' | 'gone']>> = {
  appear: [APPEAR_MS, 'arrived'],
  fly: [FLY_MS, 'arrived'],
  disappear: [DISAPPEAR_MS, 'gone'],
}

interface Props {
  lesson: LessonMode
  bridge: OverlayBridge
  /** Esc, the close button or main asked to close: Scribbly leaves, then the window closes. */
  dismissed: boolean
  onDismiss: () => void
  /** Injected in tests; the browser defaults are used otherwise. */
  narration?: Narration & { unlock?: () => Promise<void> }
  ticker?: Ticker
  fetchImpl?: typeof fetch
}

function useWindowSize(): Size {
  const read = () => ({ w: window.innerWidth, h: window.innerHeight })
  const [size, setSize] = useState(read)
  useEffect(() => {
    const onResize = () => setSize(read())
    window.addEventListener('resize', onResize)
    return () => window.removeEventListener('resize', onResize)
  }, [])
  return size
}

/** A highlight loop or "wrong" mark is being drawn: Scribbly points at it. */
function isPointing(scene: BoardScene): boolean {
  return scene.frame.prims.some(
    (d) =>
      d.progress > 0 &&
      d.progress < 1 &&
      (d.prim.type === 'highlight' || d.prim.type === 'mark_wrong'),
  )
}

/** Parts of the overlay the student looks at; the rest of the window is their own screen. */
const LESSON_PARTS = '.overlay-board, .overlay-dock, [data-interactive]'

/**
 * Calls `leave` after `LINGER_MS` while `over`, restarting whenever the pointer moves over
 * the lesson. Electron forwards every mouse move on the display to this full-screen window,
 * so moves elsewhere (the student back at work in another app) must not keep it open.
 */
function useLeaveWhenOver(over: boolean, leave: () => void) {
  useEffect(() => {
    if (!over) return
    let timer = setTimeout(leave, LINGER_MS)
    let last = ''
    const onMove = (e: MouseEvent) => {
      const at = `${e.screenX},${e.screenY}`
      const onLesson = e.target instanceof Element && e.target.closest(LESSON_PARTS) !== null
      if (at === last || !onLesson) return // re-sent moves and moves elsewhere
      last = at
      clearTimeout(timer)
      timer = setTimeout(leave, LINGER_MS)
    }
    document.addEventListener('mousemove', onMove)
    return () => {
      clearTimeout(timer)
      document.removeEventListener('mousemove', onMove)
    }
  }, [over, leave])
}

/** Scribbly's movements: pop in from a corner, fly to the lesson, act, leave. */
function useMascotMotion(scene: BoardScene, placement: Rect, size: Size, dismissed: boolean) {
  const [motion, dispatch] = useReducer(nextMotion, HIDDEN)
  const activity = activityFor(scene.mood, isPointing(scene))
  const [x, y] = boardToWindow(scene.mascotAt, scene.view, placement)
  const [cx, cy] = nearestCorner(placement, size)

  useEffect(() => dispatch({ type: 'summon', from: [cx, cy] }), [cx, cy])
  useEffect(() => dispatch({ type: 'want', activity, at: [x, y] }), [activity, x, y])
  useEffect(() => {
    if (dismissed) dispatch({ type: 'dismiss' })
  }, [dismissed])
  useEffect(() => {
    const timed = TIMED[motion.motion]
    if (!timed) return
    const timer = setTimeout(() => dispatch({ type: timed[1] }), timed[0])
    return () => clearTimeout(timer)
  }, [motion.motion])
  return motion
}

export function LessonOverlay(props: Props) {
  const { lesson, bridge, dismissed, onDismiss, fetchImpl } = props
  const [audio] = useState(() => props.narration ?? new BrowserNarration())
  const [player] = useState(() => new LessonPlayer(audio, props.ticker ?? animationFrameTicker))
  const state = useSyncExternalStore(player.subscribe, player.getState)
  const [demo, setDemo] = useState(false)
  const size = useWindowSize()
  const placement = boardPlacement(lesson.region, size)
  const scene = useBoardScene(state)
  const motion = useMascotMotion(scene, placement, size, dismissed)
  useClickThrough(bridge)
  const over = state.status === 'finished' || state.status === 'error'
  useLeaveWhenOver(over && !dismissed, onDismiss)

  useEffect(() => {
    const controller = new AbortController()
    const { imagePngBase64, settings } = lesson
    void audio.unlock?.()
    player.setSpeed(settings.speed)
    player.begin([])
    const deliver = (event: LessonEvent) => {
      if (!controller.signal.aborted) player.receive(event)
    }
    streamEvents(
      '/explain-region',
      {
        image_png_base64: imagePngBase64,
        voice: settings.voice,
        topic: demoTopicTitle(settings.demoTopic),
      },
      deliver,
      {
        signal: controller.signal,
        fetchImpl,
        onOpen: (headers) => setDemo(headers.get(DEMO_HEADER) === '1'),
      },
    ).catch((error: unknown) => {
      if (controller.signal.aborted) return
      player.fail(t(error instanceof StreamError ? `error.${error.code}` : 'error.server'))
    })
    return () => {
      controller.abort()
      player.dispose()
    }
  }, [lesson, audio, player, fetchImpl])

  useEffect(() => {
    if (dismissed) player.dispose()
  }, [dismissed, player])

  useEffect(() => {
    if (dismissed && motion.motion === 'hidden') bridge.closeLesson()
  }, [dismissed, motion.motion, bridge])

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onDismiss()
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [onDismiss])

  const step = state.status === 'running' ? state.steps[state.index] : undefined
  const checkpoint =
    step?.checkpoint && (state.stage === 'answer' || state.stage === 'feedback')
      ? step.checkpoint
      : null
  const dock = dockRect(placement, size, DOCK_HEIGHT)
  const second = lesson.settings.subtitles
  const playing = state.status === 'running' && !state.paused
  const [mx, my] = motion.at

  return (
    <div className="overlay-lesson" data-dismissed={dismissed ? 'true' : 'false'}>
      <div
        className="overlay-board"
        style={{ left: placement.x, top: placement.y, width: placement.w, height: placement.h }}
      >
        <BoardView
          state={state}
          scene={scene}
          title={state.meta?.title ?? t('app.title')}
          showMascot={false}
        />
        {checkpoint && step && (
          <div data-interactive>
            <CheckpointCard
              key={step.id}
              checkpoint={checkpoint}
              feedback={state.feedback}
              onAnswer={(input) => player.answer(input)}
              onNext={() => player.next()}
            />
          </div>
        )}
      </div>
      <div className="overlay-dock" style={{ left: dock.x, top: dock.y, width: dock.w }}>
        <div className="overlay-subtitles">
          {demo && (
            <p className="badge demo" data-testid="demo">
              {t('overlay.demo')}
              {second !== 'off' && <span lang={second}> · {t('overlay.demo', second)}</span>}
            </p>
          )}
          <Subtitles state={state} settings={{ english: true, second }} />
          {state.status === 'finished' && (
            <p className="overlay-goodbye" role="status">
              {t('overlay.goodbye')}
              {second !== 'off' && <span lang={second}> · {t('overlay.goodbye', second)}</span>}
            </p>
          )}
        </div>
        <Pill
          state={state}
          onPlay={() => player.play()}
          onPause={() => player.pause()}
          onReplay={() => player.replayStep()}
          onSpeed={(speed) => player.setSpeed(speed)}
          onClose={onDismiss}
          escapeTaken={lesson.escapeTaken}
        />
      </div>
      <svg className="overlay-mascot" aria-hidden="true">
        {motion.motion !== 'hidden' && (
          <g
            data-interactive
            data-motion={motion.motion}
            className="overlay-mascot-hit"
            onClick={() => (playing ? player.pause() : player.play())}
          >
            <Scribbly
              state={poseFor(motion.motion)}
              x={mx}
              y={my}
              mouth={state.mouth}
              scale={MASCOT_SCALE}
              below={my < MASCOT_HEADROOM}
            />
          </g>
        )}
      </svg>
    </div>
  )
}
