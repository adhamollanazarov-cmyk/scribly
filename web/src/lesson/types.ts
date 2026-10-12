// Lesson contract as streamed by the server (docs/LESSON_SCHEMA.md, shared/lesson.schema.json).
// Templates are already expanded server-side, so `template` never reaches the renderer.

export type Color =
  | 'ink'
  | 'accent'
  | 'charge_pos'
  | 'charge_neg'
  | 'field'
  | 'surface'
  | 'force'
  | 'highlight'
  | 'wrong'
  | 'right'

export type XY = [number, number]

interface Base {
  id: string
  color?: Color | null
  at?: number | null
  label?: string | null
  group?: string | null
}

export interface PointPrim extends Base {
  type: 'point'
  x: number
  y: number
  r?: number
}
export interface LinePrim extends Base {
  type: 'line' | 'arrow'
  x1: number
  y1: number
  x2: number
  y2: number
  dashed?: boolean
}
export interface VectorPrim extends Base {
  type: 'vector'
  from: XY
  to: XY
  name: string
}
export interface CirclePrim extends Base {
  type: 'circle'
  cx: number
  cy: number
  r: number
  dashed?: boolean
}
export interface EllipsePrim extends Base {
  type: 'ellipse'
  cx: number
  cy: number
  rx: number
  ry: number
  dashed?: boolean
}
export interface RectPrim extends Base {
  type: 'rect'
  x: number
  y: number
  w: number
  h: number
  dashed?: boolean
}
export interface PolylinePrim extends Base {
  type: 'polyline'
  points: XY[]
  closed?: boolean
}
export interface CurvePrim extends Base {
  type: 'curve'
  points: XY[]
}
export interface TextPrim extends Base {
  type: 'text'
  x: number
  y: number
  text: string
  size?: number | null
}
export interface MathPrim extends Base {
  type: 'math'
  x: number
  y: number
  latex: string
  size?: number | null
}
export interface SymbolPrim extends Base {
  type: 'symbol'
  x: number
  y: number
  symbol: string
  meaning: string
  unit?: string | null
}
export interface AxesPrim extends Base {
  type: 'axes'
  x: number
  y: number
  w: number
  h: number
  xlabel: string
  ylabel: string
}
export interface PlotPrim extends Base {
  type: 'plot'
  axes_id: string
  expr: string
  x_min: number
  x_max: number
  y_min: number
  y_max: number
  samples?: number
}
export interface TargetPrim extends Base {
  type: 'highlight' | 'erase'
  target_id: string
}
export interface MarkWrongPrim extends Base {
  type: 'mark_wrong'
  target_id: string
  reason: string
}
export interface TemplatePrim extends Base {
  type: 'template'
  name: string
  params: Record<string, unknown>
}

export type Primitive =
  | PointPrim
  | LinePrim
  | VectorPrim
  | CirclePrim
  | EllipsePrim
  | RectPrim
  | PolylinePrim
  | CurvePrim
  | TextPrim
  | MathPrim
  | SymbolPrim
  | AxesPrim
  | PlotPrim
  | TargetPrim
  | MarkWrongPrim
  | TemplatePrim

export type PrimitiveType = Primitive['type']

export const PRIMITIVE_TYPES: readonly PrimitiveType[] = [
  'point',
  'line',
  'arrow',
  'vector',
  'circle',
  'ellipse',
  'rect',
  'polyline',
  'curve',
  'text',
  'math',
  'symbol',
  'axes',
  'plot',
  'highlight',
  'mark_wrong',
  'erase',
  'template',
]

export interface Checkpoint {
  question: string
  type: 'choice' | 'number'
  choices?: string[] | null
  answer: number
  tolerance?: number | null
  unit?: string | null
  hint?: string | null
  reexplain_hint?: string | null
}

export interface Rect {
  x: number
  y: number
  w: number
  h: number
}

export interface Step {
  id: string
  kind: 'explain' | 'checkpoint' | 'summary' | 'branch'
  say: string
  subtitles?: { uz?: string | null; ru?: string | null }
  draw: Primitive[]
  focus?: Rect | null
  checkpoint?: Checkpoint | null
  sliders?: unknown[]
  warning?: 'unverified' | null
  audio_url: string | null
}

export interface LessonMeta {
  id: string
  title: string
  level: 'simple' | 'university' | 'exam'
  step_count: number | null
}

export type LessonEvent =
  | { event: 'meta'; data: LessonMeta }
  | { event: 'step'; data: Step }
  | { event: 'done'; data: { id: string } }
  | { event: 'error'; data: { message: string } }

export interface LessonRequest {
  type: 'topic' | 'problem'
  text: string
}
