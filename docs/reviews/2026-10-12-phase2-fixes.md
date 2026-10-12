# Phase 2 STATUS follow-up — 2026-10-12

Scope: the five issues recorded in the Phase 2 STATUS entry, on the user-requested
`claude/phase2-review` branch, based on `claude/phase2` at `56f0316`.
All verification used fake providers or intercepted browser traffic. No live
Anthropic or edge-tts requests were made. Locations below refer to the fix.

| Severity | File:line | Problem | Applied fix and regression evidence |
|---|---|---|---|
| med | `server/app/tts.py:27` | Transient edge-tts errors leave silent steps. | Two attempts with fresh streams/buffers, a 4 s deadline each and 0.2 s backoff. Cancellation propagates; only complete successful audio reaches the cache. Tests cover network failure after partial audio, empty output, timeout, persistent failure, cache reuse and cancellation. Persistent failure/autoplay refusal displays a localized notice and English narration even if English subtitles were disabled (`web/src/ui/Subtitles.tsx:24`; App regression test). |
| med | `tests/fixtures/lessons/circ_series.json:248` | Circuit legends/formulas overlap; the equivalent-resistance equation overflows the board. | Give every legend its own row, put equations below the diagram, and separate the symbolic resistance equation from its numerical substitution. Preserve the physics and narration. Chromium finishes every step/checkpoint, compares measured and actual formula bounds, checks every legend/formula lies inside 1600×1000 and checks all pairs for overlap. Generated SSE refreshed. |
| low | `web/src/board/measure.ts:28` | Estimated text/formula widths misplace highlights/pen; Caveat lacks superscript minus. | Measure full SVG glyph advances and HTML/KaTeX bounds; refresh after fonts load, not on playback ticks. Render Unicode super/subscript digits/signs using ordinary Caveat glyphs at script size. Unit tests cover measured targets/pen placement; Chromium verifies real bounds, a fraction's highlight and the superscript-minus/prefix pen position after its movement transition. |
| low | `web/src/App.tsx:27`, `web/vite.config.ts:12` | JavaScript bundle exceeds 500 kB. | Lazy-load the board and split KaTeX. A Vitest production-build test requires the dynamic board entry, the KaTeX chunk, and every JS chunk below 500,000 bytes. Build: entry 250.50 kB, board 43.67 kB, KaTeX 258.92 kB. This splits download units; total JS size is not claimed to fall below 500 kB. |
| low | `server/app/lesson/templates.py:310`, `server/app/lesson/models.py:149` | Bare plots are silently skipped by the renderer. | Require explicit finite increasing x/y ranges and earlier axes; sample 2–200 points through the existing safe expression parser, then emit a curve preserving id/timing/label/color. No browser expression evaluation. Golden `plot_square` covers cross-step axes and a later highlight. Tests reject unsafe expressions, domain errors, unknown/wrong axes, bad ranges, nonfinite values and excessive samples. Chromium plays the sampled curve/highlight end to end. |

The bare-plot change intentionally requires `y_min` and `y_max` on raw plots that
previously could not be rendered. Updated together: schema documentation,
Pydantic, generated JSON Schema, generation prompt/draft type catalogue,
TypeScript and fixtures/streams. Existing `axes_plot` templates remain supported.
Missing scales fail validation; the server does not invent them.

Validation in Windows PowerShell 5.1:

| Command (from its AGENTS §6 directory) | Result |
|---|---|
| `uv run pytest` | 601 passed (580 at baseline) |
| `uv run ruff check .` | Passed |
| `uv run ruff format --check .` | 67 files already formatted |
| `uv run mypy app` | Passed, 27 files |
| `uv run mypy scripts` | Passed, 5 files |
| `uv run python -m scripts.gen_schema` | Regenerated; schema freshness tests pass |
| `uv run python -m scripts.gen_streams` | Four streams regenerated; freshness tests pass |
| `npm test` | 92 passed (86 at baseline); includes an in-memory production build |
| `npm run lint` | ESLint and TypeScript passed, including browser-test DOM types |
| `npm run format:check` | Passed |
| `npx playwright test` | 6 passed, including the unchanged Gauss end-to-end audio/drawing test |
| `npm run build` (additional) | Passed; largest JS chunk 258.92 kB |

No new dependencies, provider response dumps, audio caches or captures are added
to Git. TTS test audio uses temporary directories; browser WAVs exist in memory.
Provider-controlled exception bodies are not included in public TTS errors.

The existing quantity/direction metadata, ideal-emf battery wording and script
typing fixes were already present and are preserved. The requested known
limitation, **prose/arrows contradict metadata**, remains for Phase 3 visual QA,
along with named/projected geometry. General AI layout planning and TTS prefetch
remain Phase 1c work. Live TTS reliability/latency was not measured; the retry
policy bounds waits but cannot make an unavailable provider speak.
