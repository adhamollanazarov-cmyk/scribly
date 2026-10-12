import { memo, useId, useMemo } from 'react'
import { t } from '../i18n'
import type { Primitive, Step, XY } from '../lesson/types'
import { Scribbly } from '../mascot/Scribbly'
import type { PlayerState } from '../player/engine'
import { mascotState } from '../player/mascotState'
import { boardFrame, type Frame, type Playhead } from './frame'
import { CANVAS, penAt, viewBoxFor, type Box } from './geometry'
import { renderLatex } from './katex'
import { PrimView } from './PrimView'
import { describeAll } from './transcript'
import { useMeasurements } from './useMeasurements'

const HOME: XY = [1440, 975] // the mascot's corner, bottom right
const ZOOM_SECONDS = 0.6
const HEADROOM = 190 // the mascot is about this tall above its pencil tip
const NO_PRIMS: Primitive[] = []

function lessonFrame(s: PlayerState, boxes: ReadonlyMap<string, Box>): Frame {
  if (s.stage === 'answer' || s.stage === 'feedback')
    return boardFrame(s.steps, s.index + 1, null, boxes)
  const playhead: Playhead | null = s.stage === 'playing' ? { schedule: s.schedule, t: s.t } : null
  return boardFrame(s.steps, s.index, playhead, boxes)
}

/** Where the last finished stroke ended: the mascot waits there between strokes. */
function lastPen(frame: Frame): XY | null {
  for (let i = frame.prims.length - 1; i >= 0; i--) {
    const { prim, progress, target, bounds } = frame.prims[i]
    const point = progress >= 1 ? penAt(prim, 1, target, bounds) : null
    if (point) return point
  }
  return null
}

function lerpBox(a: Box, b: Box, k: number): Box {
  const mix = (p: number, q: number) => p + (q - p) * k
  return { x: mix(a.x, b.x), y: mix(a.y, b.y), w: mix(a.w, b.w), h: mix(a.h, b.h) }
}

function viewFor(steps: Step[], index: number, t: number): Box {
  const current = viewBoxFor(steps[index]?.focus)
  const previous = viewBoxFor(steps[index - 1]?.focus)
  return lerpBox(previous, current, Math.min(1, t / ZOOM_SECONDS))
}

/** Visually hidden text version of the board: each shown step's narration, words and formulas. */
const BoardTranscript = memo(function BoardTranscript({
  id,
  intro,
  steps,
}: {
  id: string
  intro: Primitive[]
  steps: Step[]
}) {
  return (
    <section id={id} className="sr-only" aria-label={t('transcript.title')}>
      <ItemList prims={intro} />
      <ol>
        {steps.map((step, i) => (
          <li key={step.id} data-step={step.id}>
            <p>
              {t('steps.step')} {i + 1}. {step.say}
            </p>
            <ItemList prims={step.draw} />
          </li>
        ))}
      </ol>
    </section>
  )
})

function ItemList({ prims }: { prims: Primitive[] }) {
  const items = describeAll(prims)
  if (!items.length) return null
  return (
    <ul>
      {items.map((item) => (
        <li key={item.id}>
          {item.latex !== undefined && (
            <span dangerouslySetInnerHTML={{ __html: renderLatex(item.latex, 'mathml') }} />
          )}
          {item.latex !== undefined && item.text && ': '}
          {item.text}
        </li>
      ))}
    </ul>
  )
}

export function Board({ state, title }: { state: PlayerState; title: string }) {
  const intro = state.intro
  const prims = useMemo(
    () => [...(intro?.prims ?? []), ...state.steps.flatMap((s) => s.draw)],
    [intro?.prims, state.steps],
  )
  const boxes = useMeasurements(prims)
  const frame = lessonFrame(state, boxes)
  const introFrame = intro
    ? boardFrame([{ draw: intro.prims }], 0, { schedule: intro.schedule, t: intro.t }, boxes)
    : null
  const pen = frame.pen ?? (intro?.visible ? introFrame?.pen : null) ?? null
  const mood = mascotState(state, pen !== null)
  const resting =
    state.status !== 'running' || state.stage === 'answer' || state.stage === 'feedback'
  const [mx, my] = pen ?? (resting ? HOME : (lastPen(frame) ?? HOME))
  const view = viewFor(state.steps, state.index, state.stage === 'playing' ? state.t : 1e9)
  const transcriptId = useId()
  const shown = Math.min(state.index + 1, state.steps.length)
  const shownSteps = useMemo(() => state.steps.slice(0, shown), [state.steps, shown])
  const introShown = intro?.visible ? intro.prims : NO_PRIMS

  return (
    <>
      <svg
        className="board"
        viewBox={`${view.x} ${view.y} ${view.w} ${view.h}`}
        preserveAspectRatio="xMidYMid meet"
        role="img"
        aria-label={title}
        aria-details={transcriptId}
        data-stage={state.stage}
        data-status={state.status}
        data-step={state.steps[state.index]?.id ?? ''}
      >
        <rect
          x={-CANVAS.w}
          y={-CANVAS.h}
          width={3 * CANVAS.w}
          height={3 * CANVAS.h}
          className="board-bg"
        />
        {introFrame && (
          <g className="board-intro" data-visible={intro?.visible ? 'true' : 'false'}>
            {introFrame.prims.map((d) => (
              <PrimView key={d.prim.id} drawn={d} />
            ))}
          </g>
        )}
        <g className="board-lesson">
          {frame.prims.map((d) => (
            <PrimView key={d.prim.id} drawn={d} />
          ))}
        </g>
        <Scribbly state={mood} x={mx} y={my} mouth={state.mouth} below={my - view.y < HEADROOM} />
      </svg>
      <BoardTranscript id={transcriptId} intro={introShown} steps={shownSteps} />
    </>
  )
}
