// Scribbly, our original mascot: a cream drop-shaped body whose top is a sharpened pencil,
// teal arms and legs, holding a glowing marker (docs/brand/scribbly-sheet.png). Layered
// SVG: legs, body, pencil tip, face (eyes, eyelids, mouth), arms, marker, effect. Each
// state picks a pose (pose.ts); the board only passes a state, the pen position and how
// open the mouth is.

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

const BELOW_SHIFT = 60 // moves the body from above the marker tip to below it
const BODY =
  'M48 -88 C56 -77 68 -62 67 -42 C66 -26 55 -15 42 -15 C28 -15 17 -26 17 -41 C17 -58 34 -71 48 -88 Z'
const EYES = [
  { cx: 34, cy: -43 },
  { cx: 52, cy: -43 },
]
const MOUTH = { x: 43, y: -34 }

/** Wood of the sharpened pencil tip: everything above a scalloped line (clipped to the body). */
const WOOD = (() => {
  let d = 'M0 -100 H100 V-65 H70'
  for (let x = 70; x > 14; x -= 8) d += ` Q${x - 4} -58 ${x - 8} -65`
  return `${d} H0 Z`
})()
const GRAPHITE = 'M0 -100 H100 V-78 Q48 -74 0 -79 Z'

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

/** A teal limb: an ink outline under a teal stroke. */
function Limb({ d, width = 7 }: { d: string; width?: number }) {
  return (
    <>
      <path d={d} className="mascot-limb-edge" strokeWidth={width + 2.6} />
      <path d={d} className="mascot-limb" strokeWidth={width} />
    </>
  )
}

function Hand({ x, y, r = 4.8 }: { x: number; y: number; r?: number }) {
  return <circle cx={x} cy={y} r={r} className="mascot-hand" />
}

function Legs({ legs }: { legs: Legs }) {
  const tuck = legs === 'tuck'
  return (
    <g data-layer="legs" data-legs={legs}>
      <ellipse
        cx={42}
        cy={tuck ? 4 : -1}
        rx={tuck ? 11 : 17}
        ry={tuck ? 2 : 3}
        className="mascot-ground"
      />
      <Limb d={tuck ? 'M35 -18 L32 -11' : 'M35 -18 L34 -6'} />
      <Limb d={tuck ? 'M50 -18 L53 -11' : 'M50 -18 L51 -6'} />
      <ellipse
        cx={tuck ? 31 : 33}
        cy={tuck ? -8 : -3.5}
        rx={5.5}
        ry={3.4}
        className="mascot-hand"
      />
      <ellipse
        cx={tuck ? 54 : 52}
        cy={tuck ? -8 : -3.5}
        rx={5.5}
        ry={3.4}
        className="mascot-hand"
      />
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
        <ellipse cx={50} cy={-24} rx={20} ry={9} className="mascot-shade" />
        <g data-layer="pencil-tip">
          <path d={WOOD} className="mascot-wood" />
          <path d={GRAPHITE} className="mascot-graphite" />
        </g>
      </g>
      <path d={BODY} className="mascot-outline" />
    </g>
  )
}

function OpenEye({ cx, cy, look }: { cx: number; cy: number; look: Pose['look'] }) {
  const [lx, ly] = look
  const ex = cx + lx * 0.6
  const ey = cy + ly * 0.6
  return (
    <g>
      <ellipse cx={ex} cy={ey} rx={4.3} ry={5.5} className="mascot-ink" />
      <circle cx={ex - 1.3} cy={ey - 2} r={1.6} className="mascot-shine" />
      <circle cx={ex + 1.4} cy={ey + 1.6} r={0.7} className="mascot-shine" />
    </g>
  )
}

const closedArc = (cx: number, cy: number) =>
  `M${cx - 4.5} ${cy + 1} Q${cx} ${cy - 5} ${cx + 4.5} ${cy + 1}`

function Eyes({ pose, blink }: { pose: Pose; blink: boolean }) {
  const shut = (i: number) => pose.eyes === 'happy' || (pose.eyes === 'wink' && i === 0)
  return (
    <g data-layer="eyes" data-eyes={pose.eyes}>
      {EYES.map((e, i) => {
        // Brows: the right one lifts while thinking.
        const lift = pose.eyes === 'up' && i === 1 ? -2.5 : 0
        return (
          <g key={e.cx}>
            <path
              d={`M${e.cx - 3.5} ${e.cy - 9 + lift} Q${e.cx} ${e.cy - 11.5 + lift} ${e.cx + 3.5} ${e.cy - 9 + lift}`}
              className="mascot-line"
              strokeWidth={1.4}
            />
            {shut(i) ? (
              <path d={closedArc(e.cx, e.cy)} className="mascot-line" strokeWidth={2} />
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
                <ellipse cx={e.cx} cy={e.cy} rx={5.6} ry={6.8} className="mascot-lid" />
                <path
                  d={`M${e.cx - 4.5} ${e.cy + 0.5} Q${e.cx} ${e.cy + 3.5} ${e.cx + 4.5} ${e.cy + 0.5}`}
                  className="mascot-line"
                  strokeWidth={1.8}
                />
              </g>
            ),
          )}
        </g>
      )}
      <ellipse cx={26} cy={-34} rx={4} ry={2.6} className="mascot-cheek" />
      <ellipse cx={60} cy={-34} rx={4} ry={2.6} className="mascot-cheek" />
    </g>
  )
}

function mouthPath({ shape, open }: MouthShape): string {
  const { x, y } = MOUTH
  switch (shape) {
    case 'smile':
      return `M${x - 5} ${y} Q${x} ${y + 4.5} ${x + 5} ${y}`
    case 'wavy':
      return `M${x - 5} ${y + 1.5} q2.5 -2 5 0 q2.5 2 5 0`
    case 'o':
      return `M${x - 2.4} ${y + 2.5} a2.4 3 0 1 0 4.8 0 a2.4 3 0 1 0 -4.8 0`
    case 'grin':
      return `M${x - 7} ${y - 1} Q${x} ${y + 15} ${x + 7} ${y - 1} Z`
    case 'open': {
      const w = 4.5 + open * 1.5
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
      <Limb d={hold ? 'M21 -30 Q13 -30 11 -38' : 'M20 -28 Q12 -22 9 -12'} />
      <Marker grip={grip} />
      {hold ? <Hand x={10.8} y={-38.6} /> : <Hand x={9} y={-12} />}
    </g>
  )
}

const FREE_ARM: Record<Arm, { d: string; hand: [number, number]; extra?: string }> = {
  down: { d: 'M64 -31 Q70 -27 70 -21', hand: [70, -19] },
  wave: { d: 'M64 -34 Q73 -40 75 -52', hand: [75, -55] },
  open: { d: 'M64 -33 Q74 -35 78 -42', hand: [79, -44] },
  point: { d: 'M64 -34 Q75 -38 84 -38', hand: [85, -38], extra: 'M89 -38 L96 -39' },
  thumb: { d: 'M64 -33 Q72 -35 73 -43', hand: [74, -46], extra: 'M74 -50 L74 -56' },
  chin: { d: 'M62 -28 Q60 -21 53 -24', hand: [51, -26] },
  ear: { d: 'M65 -38 Q74 -43 72 -52', hand: [71, -54] },
  back: { d: 'M64 -30 Q72 -27 80 -27', hand: [82, -27] },
}

function FreeArm({ arm }: { arm: Arm }) {
  const { d, hand, extra } = FREE_ARM[arm]
  return (
    <g data-layer="arm-free" data-arm={arm}>
      <Limb d={d} />
      {extra && <Limb d={extra} width={3.4} />}
      <Hand x={hand[0]} y={hand[1]} />
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
          <Legs legs={pose.legs} />
          <Body clipId={`${id}-body`} />
          <Eyes pose={pose} blink={blink} />
          <Mouth mouth={mouthShape(pose, mouth)} />
          <FreeArm arm={pose.arm} />
          {!drawGrip && <MarkerArm grip="hold" />}
          <EffectLayer effect={pose.effect} />
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
