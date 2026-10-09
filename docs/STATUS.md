# Status

Update this file at the end of every task (newest entry on top, 3–8 lines).

## 2026-10-09 — claude — Phase 1a lesson engine (no AI)
**Done:** Pydantic lesson models and generated `shared/lesson.schema.json` (`uv run python -m scripts.gen_schema`; a test fails if stale). Hand-written `gauss_law.json` (7 steps, 1 checkpoint, calc 338.8 N·m²/C, uz subtitles). 7 templates, safe SymPy calc verification, TTSProvider + edge-tts + hashed audio cache, `POST /lessons` SSE in mock mode, `GET /audio/{key}.mp3`. Schema gaps filled and documented: `group`, nullable `audio_url`, `warning`.
**Checks:** PowerShell 5.1: 133 pytest, ruff, format, mypy; web 5 Vitest, eslint+tsc, Prettier, 1 Playwright. Live: uvicorn + real edge-tts streamed meta at 0.0 s, step 1 at 2.7 s, all 7 steps by 37.9 s; MP3s served as audio/mpeg.
**Next:** Phase 1b: Claude lesson generation with prompt caching, retry once on validation error, the 3 CLAUDE.md test inputs.
**Found issues:** med — edge-tts takes 2.6–12.5 s per step on this network, so later steps can arrive after the previous narration ends; synthesize step N+1 while step N is sent (Phase 1b). low — bare `plot` primitive is undrawable (no y-range, browser has no SymPy); propose server-side sampling into `curve` with explicit y_min/y_max. low — calc `unit` is not checked dimensionally. low — PyPI downloads on this machine are very slow (~1.6 MB/min at times); `uv sync` for sympy took most of an hour.

## 2026-10-09 — codex — scaffold review fixes
**Done:** Committed the original review tests/status separately as `72f2b9b` on `codex/scaffold-review`, then resolved all four findings.
- Model checks have one 10-second deadline across pagination, zero SDK retries, nonfatal timeout handling, safe status/SDK-type logging, and async cleanup of owned clients; injected clients remain caller-owned.
- Aligned package/lockfile engines and README to Node ^22.22.2 || ^24.15.0 || >=26.0.0; checked version boundaries against every locked dependency's engine requirement. No dependency versions changed.
**Checks:** PowerShell 5.1, Node 24.19.0, MOCK_AI=1: 37 pytest (12 new timeout/privacy/lifecycle cases), ruff lint/format, mypy, 5 Vitest, eslint+tsc, Prettier, and 1 Chromium Playwright test pass.
**Next:** Phase 1 lesson engine; schema/model/fixture consistency and Gauss playback remain deferred to Phases 1–2.
**Found issues:** None outstanding from the scaffold review; no new dependencies, secrets, captured images, or lesson contract changes.

## 2026-10-09 — codex — scaffold review
**Done:** Reviewed `claude/scaffold` (`699d790`) against docs-only baseline `a6a57a8` on `codex/scaffold-review`; no high-severity issues or production changes. Added 12 server tests and 2 locale tests; strengthened mock startup isolation and closed test clients.
**Checks:** PowerShell 5.1, MOCK_AI=1: 25 pytest, ruff lint/format, mypy, 5 Vitest, eslint+tsc, Prettier, and 1 Chromium Playwright test pass. No tracked secrets/captured media found; lesson schema/models/fixtures and Gauss playback are deferred to Phases 1–2.
**Next:** Builder should resolve the review findings below before Phase 1; no new dependencies or contract changes.
**Found issues:** med — `server/app/model_check.py:36` / `server/app/main.py:25`: awaited startup check inherits SDK 600-second timeout and 2 retries; bound total check time and continue on timeout.
- med — `server/app/model_check.py:44`: logs raw upstream error message/body; synthetic marker reached logs. Log status plus safe identifiers, omitting response content.
- med — `web/package.json:43` / `README.md:19`: Node >=22 admits versions unsupported by locked tools (jsdom requires ^22.22.2 || ^24.15.0 || >=26.0.0); align engines and prerequisites with the full toolchain.
- low — `server/app/model_check.py:36`: internally created AsyncAnthropic client is never explicitly closed; close owned clients in finally/context manager while leaving injected clients caller-owned.

## 2026-10-08 — claude — model id revert + startup model check
**Done:**
- Reverted `FAST_MODEL` default to `claude-haiku-5-5` (AGENTS §3, `server/app/settings.py`, `.env.example`).
- `server/app/model_check.py`: when `MOCK_AI=0`, startup lists models via the Models API and logs an error if `LESSON_MODEL`/`FAST_MODEL` is missing, or if the key is unset, rejected or the API is unreachable. Startup always continues. Added the `anthropic` SDK.
- Checks: server 13 pytest, ruff, format, mypy all pass. Live run with an invalid key logged `ERROR: Model check failed: ANTHROPIC_API_KEY was rejected (401).`
**Next:**
- With a real key in `.env`, start the server once and confirm no model-check error.
**Found issues:**
- None.

## 2026-10-08 — claude — Phase 0 scaffold
**Done:**
- Monorepo layout per AGENTS §2: `server/` (FastAPI, uv, `/health`, typed settings from `.env`), `web/` (Vite + React + TS strict, ESLint, Prettier, Vitest, Playwright smoke test), `desktop/`, `shared/`, `tests/fixtures/lessons/` placeholders.
- `.env.example`, `.gitattributes`, README with PowerShell steps. AGENTS §6 rewritten for PowerShell 5.1.
- All checks pass on Windows PowerShell 5.1 (server: 5 pytest, ruff, format, mypy; web: 3 vitest, eslint+tsc, prettier, build, 1 Playwright).
**Next:**
- Phase 1 lesson engine (PROMPTS.md). `gauss-lesson.spec.ts` (AGENTS §8) arrives with Phase 2.
**Found issues:**
- AGENTS §8 requires `gauss-lesson.spec.ts`, which cannot exist before Phase 2; treat it as N/A until then.

## YYYY-MM-DD — <agent> — <task>
**Done:**
-
**Next:**
-
**Found issues:**
-
