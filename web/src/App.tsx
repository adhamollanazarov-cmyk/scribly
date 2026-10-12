import {
  lazy,
  Suspense,
  useCallback,
  useEffect,
  useRef,
  useState,
  useSyncExternalStore,
} from 'react'
import { t } from './i18n'
import { StreamError, streamLesson } from './lesson/client'
import { introPrimitives } from './lesson/intro'
import type { LessonRequest } from './lesson/types'
import { LessonPlayer, type Narration, type Ticker } from './player/engine'
import { BrowserNarration, animationFrameTicker } from './player/narration'
import { CheckpointCard } from './ui/CheckpointCard'
import { Controls, type SubtitleSettings } from './ui/Controls'
import { LessonForm } from './ui/LessonForm'
import { StepList } from './ui/StepList'
import { Subtitles } from './ui/Subtitles'

const INTRO_LABELS = {
  problem: t('board.problem'),
  topic: t('board.topic'),
  given: t('board.given'),
}
const Board = lazy(() => import('./board/Board').then((m) => ({ default: m.Board })))

function errorMessage(error: unknown): string {
  return t(error instanceof StreamError ? `error.${error.code}` : 'error.server')
}

interface AppProps {
  /** Injected in tests; the browser defaults are used otherwise. */
  narration?: Narration & { unlock?: () => Promise<void> }
  ticker?: Ticker
  fetchImpl?: typeof fetch
}

function App({ narration, ticker, fetchImpl }: AppProps) {
  const [audio] = useState(() => narration ?? new BrowserNarration())
  const [player] = useState(() => new LessonPlayer(audio, ticker ?? animationFrameTicker))
  const state = useSyncExternalStore(player.subscribe, player.getState)
  const [subtitles, setSubtitles] = useState<SubtitleSettings>({ english: true, second: 'uz' })
  const request = useRef<AbortController | null>(null)

  useEffect(() => () => player.dispose(), [player])

  const start = useCallback(
    (lesson: LessonRequest) => {
      request.current?.abort()
      const controller = new AbortController()
      request.current = controller
      void audio.unlock?.() // inside the click: allows sound and lip sync
      player.begin(introPrimitives(lesson, INTRO_LABELS))
      streamLesson(lesson, (event) => player.receive(event), controller.signal, fetchImpl).catch(
        (error: unknown) => {
          if (!controller.signal.aborted) player.fail(errorMessage(error))
        },
      )
    },
    [audio, player, fetchImpl],
  )

  const step = state.status === 'running' ? state.steps[state.index] : undefined
  const checkpoint =
    step?.checkpoint && (state.stage === 'answer' || state.stage === 'feedback')
      ? step.checkpoint
      : null

  return (
    <div className="app">
      <header className="app-header">
        <h1>{t('app.title')}</h1>
        <p className="muted">{t('app.tagline')}</p>
      </header>
      <main className="layout">
        <section className="stage">
          <LessonForm onSubmit={start} />
          <div className="board-frame">
            <Suspense fallback={<p className="muted">{t('board.loading')}</p>}>
              <Board state={state} title={state.meta?.title ?? t('app.title')} />
            </Suspense>
            {checkpoint && step && (
              <CheckpointCard
                key={step.id}
                checkpoint={checkpoint}
                feedback={state.feedback}
                onAnswer={(input) => player.answer(input)}
                onNext={() => player.next()}
              />
            )}
          </div>
          <Subtitles state={state} settings={subtitles} />
          <Controls
            state={state}
            subtitles={subtitles}
            onPlay={() => player.play()}
            onPause={() => player.pause()}
            onRestart={() => player.restart()}
            onReplay={() => player.replayStep()}
            onSpeed={(speed) => player.setSpeed(speed)}
            onSubtitles={setSubtitles}
          />
        </section>
        <aside className="sidebar">
          {state.meta && <h2 className="lesson-title">{state.meta.title}</h2>}
          <StepList state={state} onJump={(i) => player.jumpTo(i)} />
        </aside>
      </main>
    </div>
  )
}

export default App
