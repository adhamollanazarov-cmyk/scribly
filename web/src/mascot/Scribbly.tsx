// Scribbly, our original mascot: a round cream body whose top is a sharpened pencil tip,
// short teal arms with mitten hands, stubby legs, holding a glowing marker
// (docs/brand/scribbly-sheet.png). Layered SVG: legs, body, pencil tip, face (eyes,
// eyelids, mouth), arms, marker, effect. Each state picks a pose (pose.ts); the board only
// passes a state, the pen position and how open the mouth is.

import { useEffect, useId, useState, type ReactNode } from 'react'
import './scribbly.css'
import {
  MARKER_HAND,
  markerPlace,
  mouthShape,
  poseOf,
  type Arm,
  type Effect,
  type Grip,
  type Legs,
  type MouthShape,
  type Pose,
} from './pose'
import type { MascotState } from './states'

export interface ScribblyProps {
  state: MascotState
  /** Marker tip position while drawing, in the parent's coordinates. */
  x: number
  y: number
  /** 0 = closed, 1 = wide open (from the narration loudness). */
  mouth?: number
  scale?: number
  /** Body under the marker tip instead of above it (used near the top edge). */
  below?: boolean
  /** Turn off timers (blinking), e.g. for snapshots. */
  still?: boolean
}

const BELOW_SHIFT = 84 // moves the body from above the marker tip to below it
/** Body center and radius in art units; the round body ends in a pencil cone on top. */
const C = { x: 43, y: -42 }
const R = 29
/** A point given in body radii from the center, as "x y". */
const at = (u: number, v: number) => `${+(C.x + u * R).toFixed(1)} ${+(C.y + v * R).toFixed(1)}`
const BODY = [
  `M${at(-0.013, -1.33)} Q${at(0.04, -1.4)} ${at(0.093, -1.33)}`, // rounded graphite tip
  `L${at(0.52, -0.73)}`, // cone, right side
  `C${at(0.82, -0.6)} ${at(1, -0.34)} ${at(1, 0)}`,
  `C${at(1, 0.58)} ${at(0.56, 1)} ${at(0, 1)}`,
  `C${at(-0.56, 1)} ${at(-1, 0.58)} ${at(-1, 0)}`,
  `C${at(-1, -0.34)} ${at(-0.82, -0.6)} ${at(-0.52, -0.73)} Z`,
].join(' ')
const EYES = [
  { cx: C.x - 13.3, cy: -39 },
  { cx: C.x + 13.3, cy: -39 },
]
const MOUTH = { x: C.x, y: -31 }

/** Wood of the sharpened pencil tip: everything above a scalloped line (clipped to the body). */
const WOOD = (() => {
  const [left, right, top, dip] = [C.x - 0.62 * R, C.x + 0.62 * R, C.y - 0.76 * R, C.y - 0.62 * R]
  const step = (right - left) / 5
  let d = `M0 -120 H100 V${top} H${right}`
  for (let x = right; x > left + 1; x -= step) d += ` Q${x - step / 2} ${dip} ${x - step} ${top}`
  return `${d} H0 Z`
})()
const GRAPHITE = `M0 -120 H100 V-75 Q${C.x} -72.5 0 -76 Z`

/** How the anchor glides to a new position: with the pen, a long flight, or a short step. */
const MOVING: Partial<Record<MascotState, string>> = {
  drawing: 'pen',
  pointing: 'pen',
  flying: 'fly',
  appearing: 'none',
}

function useBlink(off: boolean): boolean {
  const [closed, setClosed] = useState(false)
  useEffect(() => {
    if (off) return
    let timer: ReturnType<typeof setTimeout>
    const schedule = (open: boolean) => {
      timer = setTimeout(
        () => {
          setClosed(open)
          schedule(!open)
        },
        open ? 2400 + Math.random() * 3000 : 140,
      )
    }
    schedule(true)
    return () => {
      clearTimeout(timer)
      setClosed(false)
    }
  }, [off])
  return closed
}

/**
 * True from the moment a flight ends until the next state change: the body squashes as it
 * lands (a one-shot CSS animation). Tracks the previous state during render, no effect.
 */
function useLanding(state: MascotState): boolean {
  const [prev, setPrev] = useState(state)
  const [landing, setLanding] = useState(false)
  if (state !== prev) {
    setPrev(state)
    setLanding(prev === 'flying' && state !== 'disappearing')
  }
  return landing
}

/** A short teal arm: an ink outline under a teal stroke. */
function Limb({ d, width = 7.5 }: { d: string; width?: number }) {
  return (
    <>
      <path d={d} className="mascot-limb-edge" strokeWidth={width + 2.6} />
      <path d={d} className="mascot-limb" strokeWidth={width} />
    </>
  )
}

// Hand shapes, drawn with the fingers along +x and the thumb on the -y side.
const MITTEN =
  'M-4.6 -1.2 C-4.6 -3.8 -2.4 -4.8 -0.2 -4.4 C0.6 -6.8 2.2 -8.6 3.8 -7.8 C5.2 -7 4.6 -5.2 3.6 -3.8 C6 -3 7.2 0.4 5.8 2.8 C4.4 5.2 0.4 5.6 -2.4 4.4 C-4 3.6 -4.6 1.6 -4.6 -1.2 Z'
const FIST =
  'M-4.4 -1 C-4.4 -3.6 -2 -4.6 0.6 -4.4 C3.6 -4.2 5.4 -2.2 5.2 0.6 C5 3.4 2.6 4.8 0 4.6 C-2.6 4.4 -4.4 2.4 -4.4 -1 Z'
const PAW =
  'M-4.6 -1.2 C-4.6 -3.8 -1.2 -5 2 -4.4 C5.6 -3.6 7.2 0.4 5.8 2.8 C4.4 5.2 0.4 5.6 -2.4 4.4 C-4 3.6 -4.6 1.6 -4.6 -1.2 Z'
const THUMB_UP = 'M-0.6 -3.6 C-1 -7.6 -0.2 -10.4 1.8 -10.4 C3.6 -10.4 3.8 -7.6 3 -3.8 Z'

/** mitten: open hand with a thumb; paw: relaxed, thumb hidden; grip: fist around the marker. */
type HandShape = 'mitten' | 'paw' | 'grip' | 'point' | 'thumb'
const HAND = { mitten: MITTEN, paw: PAW, grip: FIST, point: FIST, thumb: FIST }
const HAND_SIZE = 1.25

/** A mitten hand at (x, y), fingers turned by `angle` (deg); `flip` puts the thumb on the other side. */
function Hand(props: { x: number; y: number; angle: number; flip?: boolean; shape?: HandShape }) {
  const { x, y, angle, flip = false, shape = 'mitten' } = props
  return (
    <g
      data-hand-shape={shape}
      transform={`translate(${x} ${y}) rotate(${angle}) scale(${HAND_SIZE} ${flip ? -HAND_SIZE : HAND_SIZE})`}
    >
      {shape === 'point' && <Limb d="M3 -0.6 L8.6 -1" width={3.4} />}
      {shape === 'thumb' && <path d={THUMB_UP} className="mascot-hand" data-part="thumb" />}
      <path d={HAND[shape]} className="mascot-hand" />
      {shape === 'mitten' && (
        <path d="M0.4 -3.9 Q1.8 -3 3.4 -3.6" className="mascot-crease" data-part="thumb" />
      )}
      {shape === 'grip' && (
        <path d="M-2.4 -3.2 Q0.6 -1 4.4 -1.8" className="mascot-crease" data-part="thumb" />
      )}
    </g>
  )
}

/** A stubby leg ending in a rounded foot; its top hides under the body. */
const leg = (fx: number, bottom: number) =>
  `M${fx - 5.4} -22 L${fx - 6.6} ${bottom - 4.5} Q${fx - 7} ${bottom} ${fx - 1.5} ${bottom} H${fx + 1.5} Q${fx + 7} ${bottom} ${fx + 6.6} ${bottom - 4.5} L${fx + 5.4} -22 Z`

function Legs({ legs }: { legs: Legs }) {
  const tuck = legs === 'tuck'
  return (
    <g data-layer="legs" data-legs={legs}>
      <ellipse
        cx={C.x}
        cy={tuck ? 1 : -4.5}
        rx={tuck ? 12 : 20}
        ry={tuck ? 2 : 3}
        className="mascot-ground"
      />
      {[C.x - 10.4, C.x + 10.4].map((fx, i) => (
        <path
          key={fx}
          d={leg(fx, tuck ? -9 : -5.5)}
          className="mascot-hand"
          transform={tuck ? `rotate(${i ? -16 : 16} ${fx} -16)` : undefined}
        />
      ))}
    </g>
  )
}

function Body({ clipId }: { clipId: string }) {
  return (
    <g data-layer="body">
      <clipPath id={clipId}>
        <path d={BODY} />
      </clipPath>
      <path d={BODY} className="mascot-body" />
      <g clipPath={`url(#${clipId})`}>
        <ellipse
          cx={C.x + 6}
          cy={C.y + 1.12 * R}
          rx={1.05 * R}
          ry={0.3 * R}
          className="mascot-shade"
        />
        <g data-layer="pencil-tip">
          <path d={WOOD} className="mascot-wood" />
          <path d={GRAPHITE} className="mascot-graphite" />
        </g>
      </g>
      <path d={BODY} className="mascot-outline" />
    </g>
  )
}

const EYE = { rx: 5.6, ry: 7 }

/** A big dark eye with two highlights: a large one up right, a small one down left. */
function OpenEye({ cx, cy, look }: { cx: number; cy: number; look: Pose['look'] }) {
  const [lx, ly] = look
  const ex = cx + lx * 0.6
  const ey = cy + ly * 0.6
  return (
    <g>
      <ellipse cx={ex} cy={ey} rx={EYE.rx} ry={EYE.ry} className="mascot-ink" />
      <circle cx={ex + 1.6} cy={ey - 2.6} r={2.2} className="mascot-shine" data-part="highlight" />
      <circle cx={ex - 1.9} cy={ey + 2.9} r={1} className="mascot-shine" data-part="highlight" />
    </g>
  )
}

const closedArc = (cx: number, cy: number) =>
  `M${cx - 5.5} ${cy + 1.5} Q${cx} ${cy - 5.5} ${cx + 5.5} ${cy + 1.5}`

function Eyes({ pose, blink }: { pose: Pose; blink: boolean }) {
  const shut = (i: number) => pose.eyes === 'happy' || (pose.eyes === 'wink' && i === 0)
  return (
    <g data-layer="eyes" data-eyes={pose.eyes}>
      {EYES.map((e, i) => {
        // Brows: the right one lifts while thinking.
        const by = e.cy - 11.5 + (pose.eyes === 'up' && i === 1 ? -2.5 : 0)
        return (
          <g key={e.cx}>
            <path
              d={`M${e.cx - 3} ${by} Q${e.cx} ${by - 2.2} ${e.cx + 3} ${by}`}
              className="mascot-line"
              strokeWidth={1.3}
            />
            {shut(i) ? (
              <path d={closedArc(e.cx, e.cy)} className="mascot-line" strokeWidth={2.2} />
            ) : (
              <OpenEye cx={e.cx} cy={e.cy} look={pose.look} />
            )}
          </g>
        )
      })}
      {blink && (
        <g data-layer="eyelids">
          {EYES.map((e, i) =>
            shut(i) ? null : (
              <g key={e.cx}>
                <ellipse
                  cx={e.cx}
                  cy={e.cy}
                  rx={EYE.rx + 1.6}
                  ry={EYE.ry + 1.8}
                  className="mascot-lid"
                />
                <path
                  d={`M${e.cx - 5.5} ${e.cy + 0.5} Q${e.cx} ${e.cy + 4} ${e.cx + 5.5} ${e.cy + 0.5}`}
                  className="mascot-line"
                  strokeWidth={2}
                />
              </g>
            ),
          )}
        </g>
      )}
      <ellipse cx={C.x - 17.6} cy={MOUTH.y} rx={4.4} ry={2.7} className="mascot-cheek" />
      <ellipse cx={C.x + 17.6} cy={MOUTH.y} rx={4.4} ry={2.7} className="mascot-cheek" />
    </g>
  )
}

function mouthPath({ shape, open }: MouthShape): string {
  const { x, y } = MOUTH
  switch (shape) {
    case 'smile':
      return `M${x - 5.5} ${y} Q${x} ${y + 5} ${x + 5.5} ${y}`
    case 'wavy':
      return `M${x - 5.5} ${y + 1.5} q2.75 -2 5.5 0 q2.75 2 5.5 0`
    case 'o':
      return `M${x - 2.6} ${y + 2.5} a2.6 3.2 0 1 0 5.2 0 a2.6 3.2 0 1 0 -5.2 0`
    case 'grin':
      return `M${x - 7.5} ${y - 1} Q${x} ${y + 16} ${x + 7.5} ${y - 1} Z`
    case 'open': {
      const w = 5 + open * 1.5
      const depth = 3 + open * 6
      return `M${x - w} ${y - 1} Q${x} ${y - 1 + depth * 2} ${x + w} ${y - 1} Z`
    }
  }
}

function Mouth({ mouth }: { mouth: MouthShape }) {
  const filled = mouth.shape === 'open' || mouth.shape === 'grin' || mouth.shape === 'o'
  return (
    <path
      data-layer="mouth"
      data-mouth={mouth.shape}
      d={mouthPath(mouth)}
      className={filled ? 'mascot-mouth' : 'mascot-line'}
      strokeWidth={filled ? 1.6 : 2}
    />
  )
}

/** The marker, tip at (0, 0), barrel along +x. */
function Marker({ grip }: { grip: Grip }) {
  const { x, y, angle } = markerPlace(grip)
  return (
    <g data-layer="marker" data-grip={grip} transform={`translate(${x} ${y}) rotate(${angle})`}>
      <circle
        r={grip === 'draw' ? 8 : 5}
        className={grip === 'draw' ? 'mascot-glow mascot-glow-pulse' : 'mascot-glow'}
      />
      <path d="M0 0 L5.5 -2.8 L5.5 2.8 Z" className="mascot-nib" />
      <rect x={5.5} y={-3.3} width={3} height={6.6} rx={1} className="mascot-collar" />
      <rect x={8.5} y={-3.9} width={18} height={7.8} rx={2.2} className="mascot-barrel" />
    </g>
  )
}

/** The marker hand. Always the same hand; only the grip changes. */
function MarkerArm({ grip }: { grip: Grip }) {
  const hold = grip === 'hold'
  return (
    <g data-layer="arm-marker" data-hand={MARKER_HAND}>
      <Marker grip={grip} />
      {/* Drawn over the marker, so the fist wraps the barrel. */}
      <Limb d={hold ? 'M20 -28 Q16 -27 13 -28' : 'M20 -24 Q15 -19 11 -14.5'} />
      {hold ? (
        <Hand x={11.9} y={-28.2} angle={150} flip shape="grip" />
      ) : (
        <Hand x={9.8} y={-13} angle={215} flip shape="grip" />
      )}
    </g>
  )
}

interface ArmShape {
  /** Shoulder to wrist: a short curve, not a long tube. */
  d: string
  hand: [number, number]
  /** Where the fingers point (deg). */
  angle: number
  flip?: boolean
  shape?: HandShape
}

const FREE_ARM: Record<Arm, ArmShape> = {
  down: { d: 'M66 -33 Q70 -30 71 -27', hand: [72, -24], angle: 80, shape: 'paw' },
  wave: { d: 'M67 -40 Q72 -43 74 -47', hand: [75.5, -50.5], angle: -80 },
  open: { d: 'M68 -36 Q73 -37 76 -39', hand: [79.5, -40.5], angle: -22 },
  point: { d: 'M68 -36 Q73 -37 76 -38', hand: [79.5, -38.5], angle: -6, shape: 'point' },
  thumb: { d: 'M68 -35 Q73 -37 75 -39', hand: [77.5, -40.5], angle: 0, shape: 'thumb' },
  chin: { d: 'M66 -27 Q64 -20 60 -19', hand: [56.5, -19.5], angle: -125, flip: true },
  ear: { d: 'M68 -42 Q72 -45 73 -48', hand: [73.5, -51.5], angle: -100 },
  back: { d: 'M67 -32 Q72 -31 76 -30', hand: [79.5, -29.5], angle: 12, shape: 'paw' },
}

function FreeArm({ arm }: { arm: Arm }) {
  const { d, hand, angle, flip, shape } = FREE_ARM[arm]
  return (
    <g data-layer="arm-free" data-arm={arm}>
      <Limb d={d} />
      <Hand x={hand[0]} y={hand[1]} angle={angle} flip={flip} shape={shape} />
    </g>
  )
}

function EffectLayer({ effect }: { effect: Effect }) {
  const lines = (ds: string[], cls = 'mascot-ray') =>
    ds.map((d) => <path key={d} d={d} className={cls} />)
  const star = (x: number, y: number, s = 1) => (
    <path
      key={`${x},${y}`}
      d={`M${x} ${y - 6 * s} L${x + 1.6 * s} ${y - 1.6 * s} L${x + 6 * s} ${y} L${x + 1.6 * s} ${y + 1.6 * s} L${x} ${y + 6 * s} L${x - 1.6 * s} ${y + 1.6 * s} L${x - 6 * s} ${y} L${x - 1.6 * s} ${y - 1.6 * s} Z`}
      className="mascot-star"
    />
  )
  let body: ReactNode = null
  switch (effect) {
    case 'burst':
      body = [
        ...lines(['M10 -72 l-6 -5', 'M8 -58 l-8 -1', 'M14 -84 l-3 -6'], 'mascot-line'),
        star(80, -78),
      ]
      break
    case 'trail':
      body = lines(['M6 -30 h-16', 'M8 -44 h-22', 'M12 -58 h-14'])
      break
    case 'rays':
      body = lines(['M86 -54 l6 -5', 'M89 -46 l8 -1', 'M82 -61 l3 -7'])
      break
    case 'thought':
      body = [70, 79, 91].map((cx, i) => (
        <circle key={cx} cx={cx} cy={-62 - i * 11} r={3 + i * 1.5} className="mascot-dot" />
      ))
      break
    case 'waves':
      body = lines(['M80 -58 Q85 -50 80 -42', 'M86 -62 Q93 -50 86 -38'], 'mascot-line')
      break
    case 'sparkle':
      body = [...lines(['M30 6 l-3 5', 'M42 8 v6', 'M54 6 l3 5']), star(8, -70), star(82, -74, 0.8)]
      break
    case 'bubbles':
      body = [
        [84, -72, 2],
        [90, -60, 1.5],
        [86, -48, 2.5],
      ].map(([cx, cy, r]) => <circle key={cy} cx={cx} cy={cy} r={r} className="mascot-dot" />)
      break
    case 'none':
      break
  }
  return (
    <g data-layer="effect" data-effect={effect}>
      {body}
    </g>
  )
}

const cleanId = (id: string) => id.replace(/[^a-zA-Z0-9_-]/g, '')

export function Scribbly(props: ScribblyProps) {
  const { state, x, y, mouth = 0, scale = 2, below = false, still = false } = props
  const pose = poseOf(state)
  const blink = useBlink(still || !pose.blinks)
  const id = cleanId(useId())
  const landing = useLanding(state)
  const drawGrip = pose.grip === 'draw'
  return (
    <g
      className="mascot-anchor"
      data-testid="mascot"
      data-state={state}
      style={{ transform: `translate(${x}px, ${y}px) scale(${scale})` }}
      data-moving={MOVING[state] ?? 'rest'}
      aria-hidden="true"
    >
      <defs>
        <filter id={`${id}-shadow`} x="-40%" y="-40%" width="180%" height="180%">
          <feDropShadow
            dx={0}
            dy={1.5}
            stdDeviation={1.8}
            floodColor="#0b2a33"
            floodOpacity={0.35}
          />
        </filter>
      </defs>
      <g className={`mascot mascot-${state}`} filter={`url(#${id}-shadow)`}>
        <g
          data-layer="figure"
          data-below={below}
          transform={below ? `translate(0 ${BELOW_SHIFT})` : undefined}
        >
          {/* Squash-and-stretch from the feet, apart from the marker on the pen. */}
          <g className="mascot-squash" data-land={landing}>
            <Legs legs={pose.legs} />
            <Body clipId={`${id}-body`} />
            <Eyes pose={pose} blink={blink} />
            <Mouth mouth={mouthShape(pose, mouth)} />
            <FreeArm arm={pose.arm} />
            {!drawGrip && <MarkerArm grip="hold" />}
            <EffectLayer effect={pose.effect} />
          </g>
        </g>
        {drawGrip && (
          // Marker tip stays on the pen; mirrored to reach up when the body is below it.
          <g transform={below ? 'scale(1 -1)' : undefined}>
            <MarkerArm grip="draw" />
          </g>
        )}
      </g>
    </g>
  )
}
