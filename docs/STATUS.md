# Status

Update this file at the end of every task (newest entry on top, 3–8 lines).

## 2026-10-08 — claude — Phase 0 scaffold
**Done:**
- Monorepo layout per AGENTS §2: `server/` (FastAPI, uv, `/health`, typed settings from `.env`), `web/` (Vite + React + TS strict, ESLint, Prettier, Vitest, Playwright smoke test), `desktop/`, `shared/`, `tests/fixtures/lessons/` placeholders.
- `.env.example`, `.gitattributes`, README with PowerShell steps. AGENTS §6 rewritten for PowerShell 5.1; `FAST_MODEL` default fixed to `claude-haiku-4-5`.
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
