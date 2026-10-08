# Decisions

One entry per non-obvious decision or new dependency. Newest on top.

| Date | Decision | Why | Agent |
|---|---|---|---|
| 2026-10-09 | Startup model check uses one 10-second deadline across pagination, zero SDK retries, and an async context for owned clients; provider errors log only status and SDK exception class | Keep startup bounded, close connections, and avoid provider-controlled content in logs; injected clients remain caller-owned | codex |
| 2026-10-09 | Web Node engines: `^22.22.2` or `^24.15.0` or `>=26.0.0` | Matches the strictest locked tooling requirements (jsdom and its CSS dependencies); excludes unsupported older patches and odd releases below 26 | codex |
| 2026-10-08 | Startup check: when `MOCK_AI=0`, list models via the Models API once and log an error if `LESSON_MODEL` or `FAST_MODEL` is missing; never blocks startup | A wrong model id should show up at startup, not on the first lesson request | founder |
| 2026-10-08 | Dep (server): `anthropic` (official SDK, 1.x) | Models API check now; Messages API in Phase 1. SDK handles pagination, retries and typed errors | claude |
| 2026-10-08 | `FAST_MODEL` stays `claude-haiku-5-5` (a same-day change to `claude-haiku-4-5` was reverted) | Haiku 5.5 exists and costs $0.10/$0.50 per MTok vs $1/$5 for Haiku 4.5 (5x more for prompts over 100K tokens) | founder |
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
