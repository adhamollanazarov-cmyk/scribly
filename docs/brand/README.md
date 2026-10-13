# Brand assets — Scribbly

Scribbly is our original mascot: a round cream body whose top is a sharpened pencil tip
(yellow wood, dark graphite point), big dark eyes with two highlights, orange cheeks,
short teal arms with mitten hands (with a thumb), stubby teal legs, and a teal marker
with a glowing yellow tip. Do not copy characters or assets from other
products.

Reference sheet: `scribbly-sheet.png` — row 1: appear, fly, draw, talk, point;
row 2: think, happy, encourage, idle, disappear.

## Where the art lives
All of Scribbly's art is a layered SVG in `web/src/mascot/Scribbly.tsx` (+ `scribbly.css`
for colors and motion). Layers, back to front: ground shadow + legs, body (outline,
shading, pencil-tip wood and graphite), eyes + eyelids + cheeks, mouth, free arm,
marker arm + marker, effect (sparkles, speed lines, thought dots…). Hands are one shape
(`Hand` in `Scribbly.tsx`) in five variants: open mitten with a thumb, relaxed paw,
fist gripping the marker, pointing fist, thumbs-up. A soft SVG drop
shadow (`feDropShadow`) keeps the cream body visible on white pages.

Which layers each state shows is pure data in `web/src/mascot/pose.ts` (`poseOf(state)`,
tested in `pose.test.ts`):

| state | eyes | mouth | free arm | legs | effect |
|---|---|---|---|---|---|
| `appearing` | open | open | wave | tuck | burst |
| `flying` | open | open | back | tuck | speed lines |
| `drawing` | open (look at tip) | lip sync | down | stand | tip glow pulses |
| `talking` | open | lip sync | open palm | stand | rays |
| `pointing` | open (look at tip) | open | point | stand | rays |
| `thinking` | look up, brow raised | wavy | chin | stand | thought dots |
| `happy` | closed ^ ^ | grin | wave | tuck (hop) | sparkles |
| `encouraging` | wink | open | thumbs up | stand | rays |
| `idle` | open, blinks | smile | down | stand | — |
| `disappearing` | wink | open | wave | stand | bubbles, fades out |
| `listening` (not on the sheet) | open | "o" | hand at ear | stand | sound waves |

Rules the art keeps:
- **The marker is always in the same hand** (on the left of the screen, `MARKER_HAND`).
  Only the grip changes: `draw` (drawing, pointing) puts the marker tip exactly on the
  anchor, so it follows the pen; `hold` raises it beside the body.
- **Blinking**: eyelids close for 140 ms every 2.4–5.4 s in states with open eyes
  (`idle` and the lesson moods); never when `still`.
- **Lip sync**: when narration is playing (`mouth` > 0.06) the mouth opens with the
  loudness in every state except `listening`.
- **Squash and stretch**, always from the feet: `appearing` pops in stretched, lands
  squashed and wobbles to rest; `flying` squashes to take off and stretches in flight;
  the first pose after a flight plays a landing squash (`data-land` on `.mascot-squash`,
  0.36 s; the marker on the pen does not move); `happy` crouches, stretches up and
  squashes on landing. Every keyframe segment has its own easing. Only the glide that
  follows the pen is linear (it updates every frame). `prefers-reduced-motion` turns all
  of this off.

## Swap contract
The web board and the desktop overlay only pass props, so a new character replaces
`Scribbly.tsx` + `scribbly.css` (and `pose.ts` if the layers change), nothing else.

`ScribblyProps`:
- `x`, `y` — the marker tip while drawing, in the parent's coordinates (the body is drawn
  above and to the right of it).
- `state` — one of `MASCOT_STATES` in `web/src/mascot/states.ts`. Every state needs a pose.
  Overlay movement durations must match `APPEAR_MS` / `FLY_MS` / `DISAPPEAR_MS` in
  `web/src/overlay/motion.ts` (pop in 0.45 s, glide 0.7 s, fade out 0.35 s); Vitest does not load CSS, so this is
  checked by hand.
- `mouth` — 0–1 loudness for lip sync; `scale`; `below` (body under the tip near the top
  edge; the board uses `HEADROOM`, the overlay `MASCOT_HEADROOM` — the art is about 85
  units tall at scale 1); `still` (no timers, for snapshots).

When the movement logic changes, update `web/src/overlay/motion.ts` (pure state machine,
tested in `motion.test.ts`), not the art component.

## Files
- `scribbly-sheet.png` — pose reference sheet (source for the SVG above).
- `desktop/resources/icon.png` (256 px), `tray.png` / `tray@2x.png` — app and tray icons,
  drawn by `desktop/scripts/make_icons.py` (`python desktop/scripts/make_icons.py desktop/resources`):
  Scribbly's head with the same shapes and colors as the SVG. The 16 px tray icon drops
  the cheeks, small eye highlights and shading. Rerun it when the art changes.
