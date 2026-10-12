// Scribbly, our original mascot: round purple body, round glasses, antenna with an
// orange tip, holds a pencil. Self-contained so the design can be swapped later: the board
// only passes a state, the pencil-tip position and how open the mouth is.

import { useEffect, useState } from 'react'
import './scribbly.css'
import type { MascotState } from './states'

export interface ScribblyProps {
  state: MascotState
  /** Pencil tip position, in the parent's coordinates. */
  x: number
  y: number
  /** 0 = closed, 1 = wide open (from the narration loudness). */
  mouth?: number
  scale?: number
  /** Body under the pencil tip instead of above it (used near the top edge). */
  below?: boolean
  /** Turn off timers (blinking), e.g. for snapshots. */
  still?: boolean
}

const BODY = { cx: 40, cy: -36, r: 28 }
const BELOW_SHIFT = 72 // moves the body from above the pencil tip to below it
const EYES = [
  { cx: 31, cy: -40 },
  { cx: 49, cy: -40 },
]
const LOOK: Record<MascotState, [number, number]> = {
  idle: [0, 0.5],
  drawing: [-2, 2.5],
  talking: [0, 0.5],
  listening: [0, 0],
  thinking: [2, -2.5],
  happy: [0, 0],
  encouraging: [0, 1],
}

function useBlink(still: boolean): boolean {
  const [closed, setClosed] = useState(false)
  useEffect(() => {
    if (still) return
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
    return () => clearTimeout(timer)
  }, [still])
  return closed
}

function mouthPath(state: MascotState, open: number): { d: string; filled: boolean } {
  if (open > 0.06) {
    const drop = 3 + open * 8
    return { d: `M32 -24 Q40 ${-24 + drop} 48 -24 Q40 ${-22 + drop * 0.35} 32 -24`, filled: true }
  }
  switch (state) {
    case 'happy':
      return { d: 'M30 -26 Q40 -14 50 -26 Q40 -20 30 -26', filled: true }
    case 'thinking':
      return { d: 'M35 -23 Q41 -25 46 -22', filled: false }
    case 'listening':
      return { d: 'M37 -23 a3 3 0 1 0 6 0 a3 3 0 1 0 -6 0', filled: false }
    default:
      return { d: 'M32 -25 Q40 -18 48 -25', filled: false }
  }
}

function Eyes({ state, blink }: { state: MascotState; blink: boolean }) {
  const [lx, ly] = LOOK[state]
  if (state === 'happy') {
    return (
      <g className="mascot-line">
        {EYES.map((e) => (
          <path
            key={e.cx}
            d={`M${e.cx - 5} ${e.cy + 1} Q${e.cx} ${e.cy - 6} ${e.cx + 5} ${e.cy + 1}`}
          />
        ))}
      </g>
    )
  }
  const ry = blink ? 0.8 : state === 'listening' ? 7.5 : 6.5
  return (
    <g>
      {EYES.map((e) => (
        <g key={e.cx}>
          <ellipse cx={e.cx} cy={e.cy} rx={6.5} ry={ry} fill="#fff" />
          {!blink && <circle cx={e.cx + lx} cy={e.cy + ly} r={3} className="mascot-ink" />}
        </g>
      ))}
    </g>
  )
}

function Glasses() {
  return (
    <g className="mascot-line" strokeWidth={1.8}>
      {EYES.map((e) => (
        <circle key={e.cx} cx={e.cx} cy={e.cy} r={9.5} fill="none" />
      ))}
      <path d="M38.5 -41 Q40 -43 41.5 -41" fill="none" />
    </g>
  )
}

function Extras({ state }: { state: MascotState }) {
  switch (state) {
    case 'thinking':
      return (
        <g className="mascot-thought">
          <circle cx={70} cy={-62} r={3} />
          <circle cx={79} cy={-72} r={4.5} />
          <circle cx={91} cy={-84} r={6} />
        </g>
      )
    case 'listening':
      return (
        <g className="mascot-waves mascot-line" fill="none" strokeWidth={2}>
          <path d="M74 -46 Q79 -36 74 -26" />
          <path d="M80 -50 Q87 -36 80 -22" />
        </g>
      )
    case 'happy':
      return (
        <g className="mascot-sparkles">
          <path d="M8 -66 l2 -6 l2 6 l6 2 l-6 2 l-2 6 l-2 -6 l-6 -2 z" />
          <path d="M74 -70 l1.5 -4.5 l1.5 4.5 l4.5 1.5 l-4.5 1.5 l-1.5 4.5 l-1.5 -4.5 l-4.5 -1.5 z" />
        </g>
      )
    case 'encouraging':
      return (
        <g>
          <path d="M66 -32 Q76 -40 78 -54" className="mascot-arm" fill="none" />
          <circle cx={78} cy={-57} r={4.5} className="mascot-body" />
          <path
            d="M80 -72 a3 3 0 0 1 5 -2 a3 3 0 0 1 5 2 q0 4 -5 7 q-5 -3 -5 -7 z"
            className="mascot-heart"
          />
        </g>
      )
    default:
      return null
  }
}

export function Scribbly(props: ScribblyProps) {
  const { state, x, y, mouth = 0, scale = 2, below = false, still = false } = props
  const blink = useBlink(still)
  const m = mouthPath(state, mouth)
  return (
    <g
      className="mascot-anchor"
      data-testid="mascot"
      data-state={state}
      style={{ transform: `translate(${x}px, ${y}px) scale(${scale})` }}
      data-moving={state === 'drawing' ? 'pen' : 'rest'}
      aria-hidden="true"
    >
      <g className={`mascot mascot-${state}`}>
        <g transform={below ? `translate(0 ${BELOW_SHIFT})` : undefined}>
          {/* antenna */}
          <path d="M44 -63 Q47 -76 56 -74" className="mascot-arm" fill="none" />
          <circle cx={56} cy={-74} r={4} className="mascot-tip" />
          {/* body */}
          <circle cx={BODY.cx} cy={BODY.cy} r={BODY.r} className="mascot-body" />
          <ellipse cx={40} cy={-14} rx={15} ry={4} className="mascot-belly" />
          <Eyes state={state} blink={blink} />
          <Glasses />
          <path
            d={m.d}
            className="mascot-line"
            fill={m.filled ? 'currentColor' : 'none'}
            strokeWidth={2.2}
          />
          <Extras state={state} />
        </g>
        {/* arm holding the pencil; mirrored to point up when the body is below the tip */}
        <g transform={below ? 'scale(1 -1)' : undefined}>
          <path d="M17 -26 Q12 -20 13 -15" className="mascot-arm" fill="none" />
          <g className="mascot-pencil">
            <line x1={4} y1={-6} x2={18} y2={-22} className="pencil-wood" />
            <line x1={0} y1={0} x2={4} y2={-6} className="pencil-lead" />
          </g>
        </g>
      </g>
    </g>
  )
}
