# Prompts — Scribbly

Copy one prompt at a time into the named agent. Wait until it is merged before the
next build prompt. Order: **build (Claude Code) → review (Codex) → test in browser
(Antigravity) → you check → merge.**

---

## Phase 0 — Scaffold  ·  Claude Code
```
Read AGENTS.md, docs/SPEC.md and docs/LESSON_SCHEMA.md.
Scaffold the monorepo exactly as AGENTS.md §2 describes:
- server/: FastAPI app with uv, ruff, mypy, pytest; health endpoint; settings from .env
  (ANTHROPIC_API_KEY, LESSON_MODEL, FAST_MODEL, MOCK_AI, TTS_VOICE).
- web/: Vite + React + TypeScript strict, eslint, prettier, vitest, Playwright.
- docs/STATUS.md and docs/DECISIONS.md (empty templates), .env.example, .gitignore
  (ignore .env, audio cache, screenshots), README with Windows PowerShell steps.
All commands in AGENTS.md §6 must work on Windows. No features yet.
Show me the plan first, then build, then run every check and report results.
```

## Phase 1 — Lesson engine  ·  Claude Code
```
Implement Phase 1 from docs/SPEC.md.
1. Pydantic models for the lesson schema (docs/LESSON_SCHEMA.md) in
   server/app/lesson/models.py; generate shared/lesson.schema.json from them.
2. Lesson system prompt (server/app/lesson/prompt.md) that enforces AGENTS.md §4
   teaching rules and the schema. Use prompt caching.
3. POST /lessons streaming SSE (meta, step, done, error). Validate every step;
   retry once with the validation error on failure.
4. Template expansion (start with point_charge, radial_field_lines,
   gaussian_sphere, charged_plane, incline_block, free_body, axes_plot).
5. Calc verification with SymPy (see schema "Calc").
6. TTSProvider interface + EdgeTTSProvider (en-US-AriaNeural), cached by hash.
7. MOCK_AI=1 serves tests/fixtures/lessons/gauss_law.json. Write that fixture by hand:
   6–8 steps (charge, field lines, Gaussian surface, count lines = flux, bigger
   surface same flux, Φ = Q/ε₀, one checkpoint, one calc).
Tests: schema validation, template expansion, calc verify pass/fail, SSE order,
mock mode. Run the three test inputs from CLAUDE.md and show me the lessons.
```

## Phase 2 — Board, voice, mascot  ·  Claude Code
```
Implement Phase 2 from docs/SPEC.md in web/.
- Board renders every primitive type from docs/LESSON_SCHEMA.md as animated
  hand-drawn SVG strokes (rough.js or perfect-freehand), KaTeX for math,
  handwriting font for text. Semantic color tokens → CSS variables (light/dark).
- Player: plays step audio and draws that step's primitives in sync (use `at`,
  scale stroke timing to audio length and speed 0.5–1.5×). Starts rendering
  step 1 while later steps stream in.
- Mascot as an original SVG component with states idle/drawing/talking/listening/
  thinking/happy/encouraging; it follows the pen tip while drawing, mouth moves
  with audio, blinks.
- Controls: play/pause, restart, speed, step list, replay step, subtitles EN + UZ.
- Playwright test gauss-lesson.spec.ts in mock mode: all steps play, audio and
  drawing both finish per step, no console errors.
```

## Phase 3 — Raise hand + checkpoints  ·  Claude Code
```
Implement Phase 3 from docs/SPEC.md.
- Raise hand: hold Space or click "?" → pause audio and drawing → capture the
  question with the Web Speech API (text box fallback) → POST /lessons/{id}/ask →
  stream `branch` steps into the side area → "Back to the lesson" resumes exactly
  where it paused.
- Checkpoints: choice and number types with tolerance and units. Correct → mascot
  happy. Wrong → request a `reexplain` branch with a different approach. Two wrongs
  → show the worked step and continue.
- Sliders on steps that define them (bind to primitive fields, live redraw).
- Add a slider to the Gauss fixture (surface radius) and a Playwright test for:
  interrupt-and-resume, wrong-then-right checkpoint.
```

## Phase 4 — Explain my screenshot + verification  ·  Claude Code
```
Implement Phase 4 from docs/SPEC.md.
- Web: paste (Ctrl+V) or upload an image; show a preview and "Explain this".
- Server: send the image to LESSON_MODEL with vision; extract problem + given
  solution; build a lesson that walks through the solution and uses `mark_wrong`
  on incorrect steps. All numbers go through `calcs`.
- The screenshot is kept in memory only, never written to disk or logs.
- Fixtures: a correct solution and one with a deliberate mistake (sign error in
  flux). Tests prove the mistake is marked and correct steps are not.
```

## Phase 5 — Windows overlay  ·  Claude Code
```
Implement Phase 5 from docs/SPEC.md in desktop/ with Electron, reusing the web
renderer (no duplicated drawing code).
- Global hotkey Ctrl+Shift+Space → dim overlay → drag-select region → capture only
  that region (desktopCapturer) → send to the Phase 4 endpoint.
- Transparent, always-on-top, click-through window that draws the lesson aligned
  to the selected region on screen; mascot walks there. Esc closes.
- Small floating panel: controls + subtitles; tray icon; settings (voice, speed,
  subtitle language). Handle multiple monitors and Windows display scaling
  (125%/150%).
- Build a Windows installer (electron-builder). Document it in README.
```

## Phase 6 — Memory, practice, export  ·  Claude Code
```
Implement Phase 6 from docs/SPEC.md: local SQLite (topics, mistakes, checkpoint
results), next-day review with 2–3 questions on weak topics, level switch
(simple / university / exam), export lesson as video (WebM, then MP4 via ffmpeg)
and PDF notes. Add tests for review scheduling and export.
```

---

## Codex — review after every Claude Code phase
```
Read AGENTS.md. Review branch <branch-name> against main.
Check: correctness, lesson schema consistency (docs/LESSON_SCHEMA.md vs Pydantic
models vs shared/lesson.schema.json vs fixtures), error handling, missing tests,
Windows compatibility of scripts, secrets or screenshots leaking to disk/logs.
Output a list: severity (high/med/low), file:line, problem, suggested fix.
Then, on a new branch codex/<task>, add the missing tests and fix only high-severity
issues. Run all checks from AGENTS.md §6 and report results. Update docs/STATUS.md.
```

## Codex — physics accuracy audit (after Phase 1 and Phase 4)
```
Read AGENTS.md §4. Generate lessons (real API, not mock) for these 10 problems:
Gauss's law for a sphere, an infinite line charge and an infinite plane; Coulomb
force between two charges; field of a dipole on its axis; capacitor with
dielectric; incline with friction; projectile range; simple pendulum period;
series-parallel circuit. For each, check every number, unit and claim by hand or
with SymPy. Report a table: problem, errors found, which rule in §4 was broken.
Propose concrete edits to server/app/lesson/prompt.md (do not apply them).
```

## Codex — security and privacy (before the university pilot)
```
Audit the repo for: API key exposure (client bundle, logs), screenshot storage,
unsafe Electron settings (contextIsolation, nodeIntegration, CSP), SSRF or path
traversal in audio cache, rate limiting on /lessons and /ask. Report and fix highs.
```

---

## Antigravity — browser QA after Phase 2, 3 and 4
```
Read AGENTS.md. Start server and web in mock mode (commands in §6).
Open http://localhost:5173 and play the Gauss's law lesson three times at speeds
0.5×, 1×, 1.5×. Check and record with screenshots:
1. Does drawing start and finish with the narration on every step?
2. Does the mascot follow the pen and move its mouth only while speaking?
3. Are labels and formulas readable, nothing overlaps, nothing off-canvas?
4. Do subtitles (EN + UZ) match the current step?
5. Phase 3+: interrupt mid-step, ask a question, resume — does it resume correctly?
   Answer a checkpoint wrong, then right.
6. Time from click to first stroke (target < 3 s with real API).
Write findings to docs/STATUS.md under "Found issues" (severity + screenshot name).
Fix only small CSS/layout issues on branch ag/<task>.
```

## Antigravity — competitor comparison (once, after Phase 3)
```
Visit Gauth (AI course canvas), sketchmind.ai, heybiro.com and boardyboo.com.
Ask each the same question: "Explain Gauss's law with a drawing."
Compare with our app on: time to first drawing, drawing clarity, voice quality,
can I interrupt, does it check my understanding, does it work on my own material.
Save a comparison table to docs/COMPETITORS.md with screenshots.
List the 5 changes that would make our app clearly better. Do not change code.
```
