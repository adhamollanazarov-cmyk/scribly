# Lesson JSON schema (v1)

The single contract between the AI, the server and the renderer.
Source of truth in code: `server/app/lesson/models.py` (Pydantic). Generated JSON
Schema: `shared/lesson.schema.json`. Keep this document, the models, the generated
schema and the fixtures in sync in the same change.

## Canvas
Virtual 1600 × 1000, origin top-left, units = px. The renderer scales to fit.
Side area for interrupt branches: x 1100–1600.

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
  "sliders": [ Slider ]
}
```
- `focus` (optional): area the renderer zooms/pans to for this step.
- Audio duration of `say` drives drawing speed; each primitive may set `at`
  (0–1, fraction of the narration when it starts). Default: evenly spaced.

## Primitive (all have `id`, `type`, optional `color`, `at`, `label`)
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
| `axes` | x, y, w, h, xlabel, ylabel |
| `plot` | axes_id, expr (SymPy, variable x), x_min, x_max |
| `highlight` | target_id (draws a loose circle around another primitive) |
| `mark_wrong` | target_id, reason (red circle + short note) |
| `erase` | target_id |
| `template` | name, params (expanded server-side into the types above) |

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

## Slider
```json
{ "id": "radius", "label": "Surface radius", "min": 60, "max": 300, "value": 150,
  "binds": ["surface1.r"] }
```

## Calc (verified by the server with SymPy before audio is generated)
```json
{ "id": "c1", "expr": "q/epsilon_0", "values": { "q": 3e-9, "epsilon_0": 8.854e-12 },
  "expected": 338.8, "unit": "N*m**2/C", "rel_tol": 0.01, "used_in_steps": ["s5"] }
```
Mismatch → regenerate once → still wrong → step gets `"warning": "unverified"`
and the narration says the number is not verified.

## Streaming
`POST /lessons` returns `text/event-stream`: `event: meta` (title, step count
estimate), then `event: step` per validated step (with `audio_url`), then
`event: done`. Errors: `event: error` with a human-readable message.

## Interrupt
`POST /lessons/{id}/ask` body `{ step_id, question, board: [Primitive ids] }` →
same stream format, steps of kind `branch`, drawn in the side area.
