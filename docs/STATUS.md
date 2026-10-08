# Status

Update this file at the end of every task (newest entry on top, 3–8 lines).

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
