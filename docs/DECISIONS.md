# Decisions

One entry per non-obvious decision or new dependency. Newest on top.

| Date | Decision | Why | Agent |
|---|---|---|---|
| 2026-10-08 | `FAST_MODEL` default is `claude-haiku-4-5` (AGENTS.md said `claude-haiku-5-5`) | `claude-haiku-5-5` does not exist; Haiku 4.5 is the latest Haiku | claude |
| 2026-10-08 | AGENTS.md §6 commands written one per line, no `&&` | The founder's machine has Windows PowerShell 5.1, where `&&` is a parse error | claude |
| 2026-10-08 | `.gitattributes` forces LF line endings | Git on Windows checks out CRLF by default, which would fail `prettier --check` | claude |
| 2026-10-08 | Dep (server): `fastapi[standard]` | Provides `fastapi dev`, uvicorn and the httpx test client in one install | claude |
| 2026-10-08 | Dep (server): `pydantic-settings` | Typed settings from `.env` + env vars, with `SecretStr` for the API key | claude |
| 2026-10-08 | Dep (server dev): `pytest`, `ruff`, `mypy`, `httpx2` | Required checks (AGENTS §5); `httpx2` silences Starlette's TestClient deprecation warning | claude |
| 2026-10-08 | Dep (web dev): ESLint (`@eslint/js`, `typescript-eslint`, react-hooks, react-refresh, `globals`, `eslint-config-prettier`) replaces oxlint | The Vite template now ships oxlint; AGENTS §5 requires ESLint | claude |
| 2026-10-08 | Dep (web dev): `prettier`, `vitest`, `jsdom`, `@testing-library/react`, `@testing-library/jest-dom`, `@playwright/test` | Formatting, unit tests with DOM, and E2E (AGENTS §5) | claude |
| 2026-10-08 | i18n via a tiny `t()` over `src/i18n/{en,uz,ru}.json`, no library | Enough for now; revisit if we need plurals or interpolation | claude |
| 2026-10-08 | Lesson JSON is the contract between AI, server and renderer | Lets us test the renderer without AI calls and swap models freely | founder |
| 2026-10-08 | edge-tts as default TTS behind a TTSProvider interface | Free natural English voices; OS voices on the founder's PC are Russian-only; Azure Speech is the planned swap | founder |
| 2026-10-08 | Web first, Windows overlay (Electron) in Phase 5 | Prove teaching quality before building the overlay | founder |
