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

## Phase 1a — Lesson engine without AI  ·  Claude Code  ✅ done 2026-10-10
Merged to main (models, schema, Gauss fixture, templates, SymPy verify, edge-tts,
SSE). See docs/STATUS.md.

## Phase 1b — Real lesson generation (quality first)  ·  Claude Code
```
Phase 1b on a new branch claude/phase1b from main. Real lesson generation.
Read AGENTS.md, docs/SPEC.md, docs/LESSON_SCHEMA.md, docs/COVERAGE.md and the
physics audit (do NOT merge that branch, just read it):
  git show codex/physics-audit:docs/audits/2026-10-09-provisional/REPORT.md
Show the plan first, then build. Needs ANTHROPIC_API_KEY in .env.

1. Reliable JSON: 7 of 10 audit lessons failed validation. Use structured outputs /
   strict tool use with the lesson JSON schema so format errors are impossible by
   construction; keep Pydantic validation + one retry with the exact error.
   Check the current Anthropic docs for Sonnet 5.5 request options (the audit found
   that `thinking: disabled` is rejected) before choosing settings.
2. Result ledger: say, labels, checkpoint answers and summaries reference calc
   results as placeholders ({c1}, {c1:3sf}) instead of writing computed numbers.
   The server fills them from SymPy-verified values, so the same number is identical
   everywhere and used_in_steps is derived automatically. A raw computed number in
   say or labels is a lint error. Given data from the problem may be written as is.
3. Teaching-rule lint in code, not only in the prompt (AGENTS §4): say target ≤26
   words (30 hard limit), ≤4 steps without a checkpoint, every symbol used in a
   formula must be introduced earlier by a drawn legend entry (design a `symbol`
   primitive: symbol, meaning, SI unit), units on every physical number.
   Violations → regenerate only that step with the list of violations.
4. Calc grammar: only allow-listed functions; tell the model explicitly (no abs,
   Min; use `lam` not `lambda`). Unsupported expressions are rejected with a clear
   message the retry can use.
5. Lesson system prompt server/app/lesson/prompt.md: AGENTS §4, the schema, the
   template catalogue with parameters, the audit's proposed blocks (adapted), and
   explicit safeguards for the audit failures: dipole on-axis field, keep full
   precision until the final rounding (projectile), checkpoint answers must match
   the exact wording (pendulum "full swings" is an integer), diagram angles must
   match labels or say "not to scale". Prompt caching on.
6. Real generation streamed step by step into the existing SSE endpoint (MOCK_AI=0).
7. Eval bank v0 (docs/COVERAGE.md §4): tests/eval/problems.yaml with 30 problems:
   the audit's 10 (use its reference-results.json as expected values) + 20 new
   (mechanics, kinematics graphs, circuits). Runner scripts/eval.py, report
   docs/eval/<date>.md with pass rate per topic, cost and latency.
8. Run the eval once. Show me the report, total cost, and the 3 worst lessons.
Tests: ledger fill/lint, rule lint, symbol legend, grammar errors, prompt-output
parsing, eval runner on 2 mocked problems. Run all AGENTS §6 checks, commit,
update docs/STATUS.md and docs/DECISIONS.md.
```

## Phase 1c — Grid layout + faster audio  ·  Claude Code
```
Phase 1c on a new branch claude/phase1c from main (after 1b is merged).
1. Grid coordinates + layout engine (docs/COVERAGE.md §2): the AI writes positions
   as [col,row] grid cells; the server converts to px; labels use label_side and are
   auto-placed; overlap and out-of-canvas checks; auto-fix or regenerate the step
   once with the problem list. Update LESSON_SCHEMA.md, models, shared schema,
   fixtures and the prompt.
2. Audio prefetch: generate TTS for step N+1 while step N is being sent, so the next
   step is ready before the current narration ends (1a measured 2.6–12.5 s per step).
3. Re-run the eval from 1b; layout problems must drop and no topic may lose >5 points.
Tests for layout (overlaps, clamping, label placement) and prefetch ordering.
Run all AGENTS §6 checks, commit, update docs/STATUS.md.
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

## Phase 7 — Coverage of all physics  ·  Claude Code
```
Implement docs/COVERAGE.md §3, §6 and grow §4. One small branch per item:
a) claude/templates-<group>: add the remaining templates group by group (mechanics,
   kinematics, electrostatics, circuits, magnetism, waves/optics, thermo, modern).
   Each template: unit test + fixture lesson + 5 eval problems using it.
b) claude/3d-subset: three.js 3D subset (COVERAGE §6) inside the board, driven by new
   primitive types (axes3d, vector3d, coil3d, surface3d). Update the schema.
c) After each group: run the full eval, attach the report, list topics below target.
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

## Codex — physics accuracy audit (after Phase 1b and Phase 4)
First run (provisional prompt): branch codex/physics-audit, 2026-10-09.
```
Read AGENTS.md §4. Generate lessons (real API, not mock) for these 10 problems:
Gauss's law for a sphere, an infinite line charge and an infinite plane; Coulomb
force between two charges; field of a dipole on its axis; capacitor with
dielectric; incline with friction; projectile range; simple pendulum period;
series-parallel circuit. For each, check every number, unit and claim by hand or
with SymPy. Report a table: problem, errors found, which rule in §4 was broken.
Propose concrete edits to server/app/lesson/prompt.md (do not apply them).
```

## Codex — eval gate (every PR that touches prompt, models, templates or layout)
```
Read docs/COVERAGE.md §4. Run the eval on main and on <branch> (same problems,
same models). Compare per topic: pass rate, numbers correct, layout problems, cost,
latency. If any topic drops by more than 5 points or the overall rate drops, mark the
PR "blocked" and list the failing problems with reasons. Write the comparison to
docs/eval/<date>-<branch>.md. Do not change prompts yourself.
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

## Antigravity — visual check of the eval lessons (after Phase 2 and Phase 7)
```
Start the app with MOCK_AI=0. Open the 10 lessons with the lowest visual or layout
scores from the latest docs/eval report. For each: screenshot every step and judge
overlaps, readability, and whether the drawing matches the narration. Add findings
to that eval report under "Visual review". Do not change code.
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
