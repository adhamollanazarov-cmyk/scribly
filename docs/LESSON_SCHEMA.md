# Lesson JSON schema (v1)

The single contract between the AI, the server and the renderer.
Source of truth in code: `server/app/lesson/models.py` (Pydantic). Generated JSON
Schema: `shared/lesson.schema.json`. Keep this document, the models, the generated
schema and the fixtures in sync in the same change.

## Canvas
Virtual 1600 × 1000, origin top-left, units = px. The renderer scales to fit.
Side area for interrupt branches: x 1100–1600.
Angles (templates) are degrees, counter-clockwise from +x as seen on screen (y points down).
`text` and `math` are anchored at (x, y) = left end of the text baseline.
All primitive, focus and template-parameter numbers must be finite, representable
floats. NaN, infinities and numeric strings that convert to them are rejected;
template expansion must also produce finite geometry.

## Lesson
```json
{
  "version": "1",
  "id": "uuid",
  "title": "Gauss's law",
  "level": "simple | university | exam",
  "source": { "type": "topic | problem | screenshot", "text": "..." },
  "steps": [ Step ],
  "calcs": [ Calc ]
}
```

## Step
```json
{
  "id": "s1",
  "kind": "explain | checkpoint | summary | branch",
  "say": "English narration, max 30 words.",
  "subtitles": { "uz": "...", "ru": "..." },
  "draw": [ Primitive ],
  "focus": { "x": 0, "y": 0, "w": 1600, "h": 1000 },
  "checkpoint": Checkpoint | null,
  "sliders": [ Slider ],
  "warning": "unverified" | null
}
```
- `say`: at most 30 words, written to be spoken (words, not symbols: "phi", not "Φ").
  Only the server's exact appended verification sentence (see Calc) is excluded
  from this count; setting `warning` alone never relaxes the limit.
- `kind: "checkpoint"` if and only if `checkpoint` is set. No more than 4 steps in a row
  without a checkpoint (a final `summary` is exempt).
- `warning`: set by the server only (see Calc). Never set by the AI.
  `prepare_lesson` rejects raw input containing this key, including explicit null.
- `focus` (optional): area the renderer zooms/pans to for this step.
- Audio duration of `say` drives drawing speed; each primitive may set `at`
  (0–1, fraction of the narration when it starts). Default: evenly spaced.

## Primitive (all have `id`, `type`, optional `color`, `at`, `label`, `group`)
Ids are unique across the whole lesson and use only letters, digits, `_` and `-`.
`group` is set by the server on primitives that came from a template (see Templates);
the AI never sets it.
`prepare_lesson` rejects raw input containing `group`, including explicit null.
The shared schema describes both the lesson and server-generated fields; these
raw-input ownership checks are enforced separately by Pydantic validation context.
`color` is a semantic token, never a hex: `ink | accent | charge_pos | charge_neg |
field | surface | force | highlight | wrong | right`.

| type | fields |
|---|---|
| `point` | x, y, r |
| `line` | x1, y1, x2, y2, dashed? |
| `arrow` | x1, y1, x2, y2, dashed? |
| `vector` | from:[x,y], to:[x,y], name (e.g. "E") |
| `circle` | cx, cy, r, dashed? |
| `ellipse` | cx, cy, rx, ry, dashed? |
| `rect` | x, y, w, h, dashed? |
| `polyline` | points:[[x,y],...], closed? |
| `curve` | points:[[x,y],...] (smooth through points) |
| `text` | x, y, text, size? (handwriting font) |
| `math` | x, y, latex, size? (KaTeX) |
| `symbol` | x, y, symbol (LaTeX), meaning, unit? (SI unit text; null = dimensionless) |
| `axes` | x, y, w, h, xlabel, ylabel |
| `plot` | axes_id, expr (SymPy, variable x), x_min, x_max, y_min, y_max, samples? (41, range 2–200) |
| `highlight` | target_id (draws a loose circle around another primitive or group) |
| `mark_wrong` | target_id, reason (red circle + short note) |
| `erase` | target_id (a primitive or a whole group) |
| `template` | name, params (expanded server-side into the types above) |

Unknown fields are rejected everywhere (`additionalProperties: false`).
JSON fields use their documented aliases: a vector requires `from`; the Python
attribute spelling `from_` is rejected as an unknown JSON field.
`target_id` must name a primitive or group drawn **earlier** (earlier step, or earlier
in the same step's `draw`). Checked after template expansion.

`symbol` is a legend entry, drawn as "Φ — electric flux (N·m²/C)". Every symbol used in
a `math` formula must first be introduced by a `symbol` entry drawn earlier (an earlier
step, or earlier in the same step's `draw`). Generated lessons are checked for this
(`server/app/lesson/lint.py`); the golden fixtures follow it too.

`plot` references an `axes` primitive drawn earlier (including in an earlier step).
Both x and y ranges are required, finite and increasing: the server does not invent
the y scale. It samples the expression with the same bounded, allowlisted parser as
`axes_plot`, maps values into the axes box (SVG y points down), and clips to the y
range. Unsafe expressions, invalid references and sampling/domain errors fail
validation before that step is streamed. The output is a `curve` with the plot's
original id, timing, label and color, so subsequent highlights/erases still work.
The browser receives points and never evaluates expressions. `plot_square.json`
and its generated stream cover this contract; `axes_plot` remains the convenience
template that creates both axes and curve.

## Templates
Expanded by the server (`server/app/lesson/templates.py`) before anything is streamed.
Each child gets id `<template id>-<part>` and `group: "<template id>"`; the template's
`at` is copied to every child, its `color` (if set) overrides the children's colors, and
its `label` goes on the first child. Use the child ids below for slider `binds`.

| name | params (defaults) | children |
|---|---|---|
| `point_charge` | x, y, sign `+`/`-` (`+`), r (16), name? | `-charge` circle, `-sign-h` line, `-sign-v` line (only for `+`) |
| `radial_field_lines` | x, y, n (8, max 36), r_start (30), r_end (200), direction `out`/`in`, angle_offset (0) | `-1` … `-n` arrows |
| `gaussian_sphere` | cx, cy, r, name? | `-sphere` dashed circle |
| `charged_plane` | x, y (centre), length (600), orientation `vertical`/`horizontal`, sign, n (5), field_length (120) | `-plane` line, `-q1` … `-qn` points, `-e1` … `-e2n` arrows (both sides) |
| `incline_block` | x, y (right-angle corner, bottom-left), base (500), angle_deg (30), block (80) | `-incline` polyline, `-block` polyline, `-angle` text |
| `free_body` | x, y, size (40), forces: [{name, angle_deg, length}] (1–8) | `-body` rect, `-f1` … `-fn` vectors |
| `axes_plot` | x, y (top-left of box), w, h, xlabel, ylabel, expr (in x), x_min, x_max, y_min?, y_max?, samples (41) | `-axes` axes, `-curve` curve |

## Checkpoint
```json
{
  "question": "If we double the sphere radius, the flux...",
  "type": "choice | number",
  "choices": ["doubles", "stays the same", "halves"],
  "answer": 1,
  "tolerance": 0.02,
  "unit": "N·m²/C",
  "hint": "Count the lines crossing the surface.",
  "reexplain_hint": "Use the 'count the lines' picture again with a bigger sphere."
}
```

`choice`: at least 2 `choices`, `answer` is the index of the correct one.
`number`: `answer` is the value, `unit` is required, `tolerance` is relative.

## Slider
```json
{ "id": "radius", "label": "Surface radius", "min": 60, "max": 300, "value": 150,
  "binds": ["surface1-sphere.r"] }
```
`min ≤ value ≤ max`. Each bind is `<primitive id>.<field>` and must name a real field of
a primitive drawn earlier (template children by their expanded ids).

## Calc (verified by the server with SymPy before audio is generated)
```json
{ "id": "c1", "expr": "q/epsilon_0", "values": { "q": 3e-9, "epsilon_0": 8.854e-12 },
  "expected": 338.8, "unit": "N*m**2/C", "rel_tol": 0.01, "used_in_steps": ["s6"] }
```
For generated lessons, `used_in_steps` is derived by the server from the result-ledger
placeholders (see "Generation draft" below); the AI never writes it.

Mismatch → regenerate once → still wrong → step gets `"warning": "unverified"`
and the narration says the number is not verified ("I could not verify this number."
is appended to `say`, once, even if an internal/reloaded step already has a warning).
Passes when |value − expected| ≤ rel_tol·|expected|. Non-finite expected values or
relative tolerances fail verification before comparison.
`expr` may use only the names in `values`, `+ - * / ^ ( )`, numbers, and
sqrt, sin, cos, tan, asin, acos, atan, exp, log, pi, E (max 200 characters). Not abs,
Min, Max, Piecewise or any other function; value names are identifiers that are not
Python keywords or function names (`lam`, not `lambda`). Errors say what to write instead.
`unit` is not checked dimensionally yet.

## Generation draft (what the AI writes)

The AI does not write the lesson above directly. It writes a **draft**
(`server/app/lesson/draft.py`), enforced with structured outputs, which the server checks
and converts step by step. The API compiles the output schema into a grammar with a small
budget (about 70 properties), so the draft is lean:

- Every field is required; `""` and `[]` replace null. Order is generation order.
- Lesson: `title, level, steps`. Step: `id, kind, calcs, say, subtitles{uz,ru}, draw,
  checkpoints` (0 or 1 item). Calcs are **step-local** and come before `say`.
- Calc: `id` (`c1`, `c2`, …), `expr`, `values: [{name, value}]`, `quantity_kind`, `frame`, `positive`, `expected`,
  `unit` (SymPy style), `unit_spoken`. `expr` may use an earlier calc id as a name; the
  server substitutes its full-precision value. `positive` says what a positive result
  means (`+x`, `-y`, `A->B`, `cw`, `down the slope`, `toward P`, …; `""` for no
  direction; vocabulary in `server/app/lesson/direction.py`); the signed value plus
  `positive` gives the physical direction. It stays in the draft and the ledger: the
  lesson's `Calc` contract is unchanged. `quantity_kind` is required: `component` or
  `oriented` requires a readable, nonempty `positive` and a nonempty, trimmed `frame`
  ID, even at zero; `scalar` and `magnitude` require both fields to be empty.
  Negative work, energy and charge may be scalars; magnitudes cannot be negative.
  Closed-surface flux with the intrinsic outward-normal definition is scalar;
  an explicitly oriented normal field component is a component. Metadata describes
  the actual quantity, never a way to avoid a direction check.
- Draw item: `id, type, color, label, frame, at, num: [{k, v}], txt: [{k, v}], pts`. `type` is a
  primitive type or a template name; arguments are the contract fields by name (vector:
  `x1,y1,x2,y2`; booleans as 1/0; `free_body` repeats `name`/`angle_deg`/`length` once
  per force; template text args set to `""` keep the default). A convention drawing
  uses the same `frame` ID as its calcs; other drawings use `""`. Frame metadata is
  consumed during generation, not sent as primitive arguments to the renderer.
- Checkpoint: `question, type, choices, answer, hint, reexplain_hint`; `answer` is the
  choice index as digits, or one placeholder (`"{c4:3sf}"`) for a number checkpoint, whose
  `unit` and `tolerance` (0.02) the server sets.

**Result ledger.** Computed numbers are written as placeholders `{c1}`, `{c1:4sf}`,
`{c1:2dp}` (default 3 significant figures). The server fills in the SymPy value plus its
unit: spoken unit in `say`, `N·m²/C` on the board, `\,\mathrm{N\cdot m^{2}/C}` in LaTeX;
scientific notation below 0.01 or from 10⁴. A number in narration, labels, text, math or
checkpoints that is neither a placeholder, a given number (also SI-rescaled), an
explicitly labelled example with units, a standard constant, nor a small whole
count is a lint error; halves and quarters (0.5, 0.25) pass only inside LaTeX formulas.
Neither `values` nor expression literals authorize themselves as physical givens.
Example declarations in narration/board text use “example”, “hypothetical” or “suppose”;
their unit-bearing numbers remain available in later steps. This is a lexical lint,
not a proof of the physical provenance or dimensional meaning of every input.
An ambiguous result near its floating-point rounding bound is rechecked at 800 decimal
digits, then checked for stability at 1000 digits, with a bounded arithmetic interpreter.
The bound selects a recheck; it does not authorize zero snapping or a tolerance match.
Unsafe intermediate underflow or unstable rechecks fail verification. The existing
expected-relative comparison still applies. True zeros such as cos 90° and q − q
store as 0; uncertain differences in rounded inputs remain nonzero and may need
repair. No value renders as "-0.00".

**Checks per step** (`stepcheck.py`, `lint.py`): draft shape → ids → calcs (SymPy, grammar)
→ ledger fill → say ≤ 30 words after filling → ≤ 4 steps without a checkpoint → symbols
in `math` introduced by an earlier `symbol` entry (unit macros need explicit spacing
after numbers or unit wrappers: `2\Omega` remains a symbol, `2\,\Omega` is a unit)
→ no hand-written computed numbers → units on given numbers → one sign convention
per reference frame (a readable `positive`, never the opposite of an earlier one in
that frame). The relevant convention must be drawn in an earlier step, or at=0 before
result annotations in the current draw list. Match canonical direction and frame;
unrelated axes/arrows cannot authorize it. Cartesian convention-arrow geometry is
checked with physical +x right, +y up (SVG y decreases); axes authorize only their
matching x/y labels (plot templates have x/y defaults). Other projected/named
geometry and result prose/arrows remain Phase 3 visual QA responsibilities.
→ contract validation, template expansion, references. A step with
problems is regenerated **once, alone**, with the exact list (the fix may insert a
checkpoint step before it). Still broken: a contract problem (words, checkpoint spacing,
placeholders, validation, sign convention) ends the lesson with an `error` event; a hand-written number
left in a step marks it `unverified`; other leftovers are logged.

## Streaming
`POST /lessons` body `{ "type": "topic" | "problem", "text": "..." }` returns
`text/event-stream`:

| event | data |
|---|---|
| `meta` | `{ id, title, level, step_count }`; `step_count` is `null` for live AI lessons (the count is known only at `done`) |
| `step` | a Step (templates already expanded, calcs verified) plus `audio_url` |
| `done` | `{ id }` |
| `error` | `{ message }`: human-readable, safe to show; the stream ends |

`audio_url` is `/audio/<64 hex>.mp3` (cacheable forever), or `null` if speech failed
for that step; the renderer then times the drawing without audio.

## Interrupt
`POST /lessons/{id}/ask` body `{ step_id, question, board: [Primitive ids] }` →
same stream format, steps of kind `branch`, drawn in the side area.
