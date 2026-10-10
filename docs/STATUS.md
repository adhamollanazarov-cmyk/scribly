# Status

Update this file at the end of every task (newest entry on top, 3–8 lines).

## 2026-10-10 — codex — Phase 1b review (`codex/phase1b-review`)
**Done:** Reviewed `claude/phase1b` (`f3d8c79`) against `main` (`a70a7ff`); fixed four high findings: ledger input overrides, primitive/group ID validation, silent final validation failures, and false eval passes. Added signed/unit-aware displayed-value grading, warning/manual-review gates, grading-version warnings and a circuit sign-convention safeguard. Full severity list: `docs/reviews/2026-10-10-phase1b.md`.
**Checks:** PowerShell 5.1, MOCK_AI=1: 403 pytest (44 additional cases), ruff lint/format, mypy, unchanged regenerated schema; 5 Vitest, ESLint+tsc, Prettier, 1 Chromium smoke test passed. No real API/TTS calls or new dependencies.
**Found issues:** Nine medium findings remain unchanged: malformed placeholders, unit-lint false positives, numeric provenance exemptions, summary pacing, fix identity/success accounting, soft cost guard, unbounded fix cost/cleanup, raw eval exception causes, owned API-client lifecycle. Existing Phase 2 Gauss playback gap remains open.
**Next:** Human merges the review branch; address medium findings. Kirchhoff direction claims require manual review; historical 30/30 eval scores were not rerun or certified under the corrected grader.

## 2026-10-10 — claude — Phase 1b real lesson generation (`claude/phase1b`)
**Done:** Real generation in `POST /lessons` (MOCK_AI=0), streamed step by step. The model writes a structured-output draft: a lean schema, because the full typed lesson exceeds the API grammar budget. The server then runs per step: SymPy calcs → result-ledger fill (`{c1:3sf}`) → teaching lint → contract checks. A step with problems is regenerated once, alone. Also: `symbol` legend primitive, `prompt.md`, eval bank v0 (30 problems), `scripts.eval`, 3 replayed prompt-test fixtures.
**Checks:** PowerShell 5.1: 359 pytest, ruff, format, mypy; web 5 Vitest, eslint+tsc, Prettier, 1 Playwright. **Eval** (`docs/eval/2026-10-10.md`): 30/30 pass, numbers 100 %, $2.89 total ($0.096/lesson), median first step 5.5 s, average lesson 34 s. A/B adaptive thinking (`2026-10-10-adaptive.md`) was cut short when the account ran out of API credit (7/10 failed with a billing 400). On the 3 that ran, both modes passed; adaptive needed 0 fixes but step 1 took ~2 min and each lesson cost ~2×. Total API spend this phase ≈ $4.2. Live route + edge-tts: meta 5.1 s, step 1 with audio 9.2 s.
**Next:** Fix the found issues below. Add sign/direction checks to the eval (it compares magnitudes only). Phase 1c: layout, plus audio prefetch for the < 3 s budget.
**Found issues:** high — the circ-kirchhoff summary states the wrong current directions while all magnitudes pass, so the eval needs direction checks and the prompt needs one sign convention. med — lint false positives: `100\,\Omega` is not seen as a unit and `\Omega` is read as a symbol. med — `0.25` slips past the raw-number rule (fraction exemption too broad outside formulas). med — a calc with `expected` 0 can never verify (relative tolerance only), and tiny values render as "-0.00". low — numbers written inside calc `expr` don't count as declared inputs; "dimensionless" is spoken as a unit.

## 2026-10-10 — founder — plan update after Phase 1a + physics audit
**Done:** Phase 1a merged. Added docs/COVERAGE.md (path to any physics problem) and
Phase 7; split Phase 1 remainder into 1b (generation quality from the audit) and 1c
(grid layout, audio prefetch). Prompts in PROMPTS.md.
**Next:** Phase 1b (Claude Code). Audit evidence stays on branch codex/physics-audit.
**Found issues:** none new.

## 2026-10-10 — codex — Phase 1a medium findings fixed
**Done:** Fixed all five medium findings on `codex/phase1a-review`: safe exception-type-only lesson logs, raw server-field rejection and idempotent spoken warnings, canonical JSON aliases, final-summary-only checkpoint exemption, finite primitive/focus/template geometry. Converted all five strict xfails into normal passing tests; added boundary tests and `force_vector.json` contract fixture.
**Checks:** PowerShell 5.1, MOCK_AI=1: 219 pytest passed with no skips/xfails; ruff lint/format, mypy, regenerated schema; 5 Vitest, ESLint+tsc, Prettier and 1 Chromium smoke test passed. Updated schema docs and review resolutions; no dependencies or real API/TTS calls.
**Found issues:** The low Phase 2 Gauss audio/drawing playback finding remains unchanged; no outstanding high/medium findings from this review.
**Next:** Human merges the review branch; Phase 2 owns the existing playback coverage gap. Full findings and fix details: `docs/reviews/2026-10-10-phase1a.md`.

## 2026-10-10 — codex — Phase 1a review
**Done:** Reviewed `claude/phase1a` (`9bdb6be`) against `main` (`097f15f`) on `codex/phase1a-review`. Fixed only two high-severity findings: floor-division bypass of unevaluated SymPy parsing, and non-finite expected values/tolerances falsely passing calc verification. Added 57 test cases; report: `docs/reviews/2026-10-10-phase1a.md`.
**Checks:** PowerShell 5.1, MOCK_AI=1: 185 pytest passed, 5 strict xfails documenting unfixed medium findings; ruff lint/format, mypy, unchanged regenerated schema; 5 Vitest, ESLint+tsc, Prettier, 1 Chromium smoke test passed. Tracked credential/media scan passed; no real API/TTS calls or contract/dependency changes.
**Found issues:** med — raw template/exception content in logs; supplied warning suppresses spoken disclaimer; `from_` accepted contrary to shared schema; intermediate summaries bypass checkpoint spacing; non-finite drawing coordinates serialize as null. low — Gauss playback E2E is absent while the web remains a Phase 2 placeholder.
**Next:** Human merges the review branch; address medium findings before Phase 1b and add real Gauss audio/drawing playback coverage with the Phase 2 renderer. Full findings include reviewed file:line locations, reproductions and suggested fixes.

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
