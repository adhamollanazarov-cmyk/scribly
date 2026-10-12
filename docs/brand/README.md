# Brand assets — Scribbly

Scribbly is our original mascot: a round purple character with round glasses, a small
antenna with an orange tip, holding a pencil (docs/SPEC.md). Do not copy characters or
assets from other products.

## Swapping in a new character
All of Scribbly's art lives in one component: `web/src/mascot/Scribbly.tsx` (+
`scribbly.css`). The web board and the desktop overlay only pass it props, so a new
character from this folder replaces that one file pair and nothing else.

Contract (`ScribblyProps`):
- `x`, `y` — the pencil tip, in the parent's coordinates (the body is drawn around it).
- `state` — one of `MASCOT_STATES` in `web/src/mascot/states.ts`. Every state needs a pose:
  - lesson moods: `idle` (bob + blink), `drawing`, `talking`, `listening`, `thinking`,
    `happy`, `encouraging`;
  - overlay movements: `appearing` (pop in, 0.45 s), `flying` (0.7 s glide),
    `pointing`, `disappearing` (pop out, 0.35 s). Durations must match
    `APPEAR_MS` / `FLY_MS` / `DISAPPEAR_MS` in `web/src/overlay/motion.ts`.
- `mouth` — 0–1 loudness for lip sync; `scale`; `below` (body under the tip near the top
  edge); `still` (no timers, for snapshots).

When the movement logic changes, update `web/src/overlay/motion.ts` (pure state machine,
tested in `motion.test.ts`), not the art component.

## Files
- `desktop/resources/icon.png` (256 px), `tray.png` / `tray@2x.png` — app and tray icons,
  drawn by `desktop/scripts/make_icons.py` (`python desktop/scripts/make_icons.py desktop/resources`).
