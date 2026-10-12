import { memo, useId, useMemo } from 'react'
import { t } from '../i18n'
import type { Primitive, Step } from '../lesson/types'
import { Scribbly } from '../mascot/Scribbly'
import type { PlayerState } from '../player/engine'
import { CANVAS } from './geometry'
import { renderLatex } from './katex'
import { PrimView } from './PrimView'
import { useBoardScene, type BoardScene } from './scene'
import { describeAll } from './transcript'

const HEADROOM = 190 // the mascot is about this tall above its pencil tip
const NO_PRIMS: Primitive[] = []

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
  return <BoardView state={state} scene={useBoardScene(state)} title={title} />
}

interface BoardViewProps {
  state: PlayerState
  scene: BoardScene
  title: string
  /** The overlay draws Scribbly in its own full-screen layer instead. */
  showMascot?: boolean
}

export function BoardView({ state, scene, title, showMascot = true }: BoardViewProps) {
  const { frame, introFrame, view } = scene
  const intro = state.intro
  const [mx, my] = scene.mascotAt
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
        {showMascot && (
          <Scribbly
            state={scene.mood}
            x={mx}
            y={my}
            mouth={state.mouth}
            below={my - view.y < HEADROOM}
          />
        )}
      </svg>
      <BoardTranscript id={transcriptId} intro={introShown} steps={shownSteps} />
    </>
  )
}
