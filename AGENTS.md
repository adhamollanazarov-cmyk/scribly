# AGENTS.md — Scribbly

Shared rules for every coding agent on this repo (Claude Code, Codex, Antigravity).
Full product spec: `docs/SPEC.md`. Lesson JSON contract: `docs/LESSON_SCHEMA.md`.
Read both before your first task. Keep this file under 12,000 characters.

## 1. What we are building
An AI teacher that **explains hard subjects (physics first) by drawing step by step
while speaking**, like a human teacher at a whiteboard, with a small original mascot.
Goal: be clearly better than HeyClicky, Meta Muse, Gauth Canvas, SketchMind, Biro.

Our edge (protect it in every decision):
1. **Works on top of whatever is on the student's screen** (ChatGPT answer, PDF,
   slide, video frame): select a region, the teacher draws and explains right there.
2. **Teaches, does not just answer**: one idea per step, checks understanding,
   re-explains differently when the student is wrong.
3. **The student can interrupt any time** ("raise hand"), ask by voice, get a drawn
   answer, then the lesson resumes.
4. **Correctness first**: numbers are verified in code before they are spoken.
5. Windows first (HeyClicky is Mac only), then phone. English voice by default,
   Uzbek and Russian subtitles.

First real user: the founder, a university student learning physics in English.

## 2. Architecture (monorepo)
```
server/      FastAPI (Python 3.12, Pydantic v2) — lesson generation, TTS, verification
web/         Vite + React + TypeScript (strict) — board renderer, mascot, controls
desktop/     Electron (Phase 5) — hotkey, region capture, transparent overlay
shared/      lesson JSON Schema generated from the Pydantic models
docs/        SPEC.md, LESSON_SCHEMA.md, STATUS.md, DECISIONS.md,
             prototype/gauss_lesson_prototype.html (look-and-feel reference)
tests/fixtures/lessons/   golden lessons (gauss_law.json is the reference lesson)
```
Pipeline: input (topic | problem text | screenshot) → Claude builds a lesson JSON →
server expands `template` primitives and verifies `calc` items with SymPy →
server makes one MP3 per step (TTS) → web plays audio while drawing strokes in sync.

## 3. Key technical rules
- **Lesson JSON is the contract** between AI, server and renderer. Change it only via
  `docs/LESSON_SCHEMA.md` + Pydantic models + regenerated `shared/` schema + fixtures,
  in the same change.
- AI output must be validated with Pydantic; on failure retry once with the
  validation error, then return a clear error. Never render unvalidated JSON.
- Models come from env: `LESSON_MODEL` (default `claude-sonnet-5-5`),
  `FAST_MODEL` (default `claude-haiku-5-5`). Use prompt caching for the long
  system prompt. Never hardcode API keys; read `ANTHROPIC_API_KEY` from `.env`.
- **Mock mode**: `MOCK_AI=1` serves golden fixtures with no API calls. All UI work
  and tests must run in mock mode.
- TTS goes through a `TTSProvider` interface. Default `edge-tts`
  (`en-US-AriaNeural`); Azure Speech is the planned swap. Cache audio by
  hash(text+voice+rate). Never rely on the OS speechSynthesis voices.
- Drawing: SVG, strokes animated along the path; hand-drawn look (rough.js or
  perfect-freehand); formulas with KaTeX; handwriting font for labels.
  Stroke timing is scaled to the step's audio duration and the speed setting.
- Latency budget: first stroke and first word **< 3 s** after request. Stream steps
  (SSE) — render step 1 while later steps are still generating.
- Coordinates: virtual canvas 1600×1000, origin top-left; the renderer scales.
- Screenshots: captured only on explicit user action, sent once, **not stored**
  unless the user saves the lesson.

## 4. Teaching rules (enforced in the lesson system prompt and in review)
- One idea per step. `say` ≤ 30 words, plain English, no jargon without a drawing.
- Every new symbol is drawn and labeled before it is used in a formula.
- Units on every number. Never invent data not given in the problem.
- A checkpoint question at least every 4 steps; wrong answer → re-explain with a
  different approach (analogy, simpler numbers, or a different drawing).
- If the AI is unsure, it says so instead of guessing.
- When explaining a pasted AI/teacher solution: walk through it, and flag any wrong
  step on the board (red circle + short reason).

## 5. Code conventions
- Python: ruff (lint + format), mypy on `server/app`, pytest. Small pure functions;
  I/O at the edges.
- TypeScript: strict, eslint, prettier, vitest; Playwright for E2E.
- No new dependency without a one-line reason in `docs/DECISIONS.md`.
- Names and comments in English. User-facing strings via i18n files (en, uz, ru).
- Do not copy names, logos, mascots or assets from HeyClicky, Meta Muse, Gauth or
  any other product. Our mascot "Scribbly" is original: round purple character, round
  glasses, holds a pencil (see `docs/SPEC.md`).

## 6. Commands (keep this section updated when they change)
One command per line: works in Windows PowerShell 5.1 (no `&&`) and in bash.
Each block starts from the repo root.
```
# server — run (http://localhost:8000)
cd server
uv sync
uv run fastapi dev app/main.py
# server — checks
uv run pytest
uv run ruff check .
uv run ruff format --check .
uv run mypy app
uv run python -m scripts.gen_schema  # after changing app/lesson/models.py
# web — run (http://localhost:5173)
cd web
npm install
npx playwright install chromium     # once, after install or Playwright upgrade
npm run dev
# web — checks
npm test
npm run lint                        # eslint + tsc
npm run format:check
npx playwright test
# mock mode (no API key needed)
$env:MOCK_AI="1"                    # PowerShell;  bash: export MOCK_AI=1
```
The founder develops on **Windows 11**: every command and script must work in
PowerShell. Avoid bash-only scripts.

## 7. Multi-agent workflow
Roles:
- **Claude Code** — main builder: features, architecture, refactors.
- **Codex** — reviewer and tester: code review, missing tests, bug fixes found in
  review, security/privacy checks.
- **Antigravity** — browser QA: runs the app, checks drawing/voice sync, UX,
  compares with competitors, files issues; small UI fixes only.

Rules:
1. **One agent edits one area at a time.** Work on your own branch:
   `claude/<task>`, `codex/<task>`, `ag/<task>`. The human merges.
2. Stay inside the task scope. If you find an unrelated problem, write it in
   `docs/STATUS.md` under "Found issues" instead of fixing it.
3. Before you start: read `docs/STATUS.md`. When you finish: update it
   (Done / Next / Found issues, 3–8 lines, dated).
4. Record any non-obvious decision in `docs/DECISIONS.md` (date, decision, why).
5. Never commit secrets, `.env`, audio caches or screenshots.

## 8. Definition of Done
- Tests, lint and type checks pass (commands in §6).
- The golden lesson `gauss_law.json` still plays end to end in mock mode with
  audio and drawing in sync (Playwright test `gauss-lesson.spec.ts`).
- New behavior has tests. Schema changes updated everywhere (see §3).
- `docs/STATUS.md` updated. The app runs on Windows with the documented commands.
