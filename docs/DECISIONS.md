# Decisions

One entry per non-obvious decision or new dependency. Newest on top.

| Date | Decision | Why | Agent |
|---|---|---|---|
| 2026-10-10 | Phase 1b = generation quality (structured outputs, result ledger with {c1} placeholders, teaching-rule lint in code, eval bank v0); grid layout + audio prefetch moved to Phase 1c | Physics audit: 7/10 lessons failed schema validation, rounding drift between narration/board/summary, symbol and checkpoint rules broken in all 10; smaller phases are easier to review | founder |
| 2026-10-10 | Add docs/COVERAGE.md and Phase 7 (all-physics coverage) with an eval gate on prompt/model/template changes | Goal is any physics problem, not only Gauss's law; quality must be measured per topic | founder |
| 2026-10-10 | Raw lesson validation uses `raw_input` context to reject server-owned `warning`/`group` keys; internal/output validation accepts them. Only the appended verification sentence may extend narration beyond 30 words. Geometry models reject non-finite floats and JSON aliases are mandatory. | Close the five medium review findings while preserving validation of expanded/verified output and idempotent spoken disclaimers; shared schema and a canonical vector fixture are checked together. | codex |
| 2026-10-10 | Validate the full arithmetic AST before the SymPy parser; only supported operators and unary functions, finite literals and depth ≤32 may reach `parse_expr`. Reject non-finite expected values/tolerances in verification. | `//` bypasses SymPy's `evaluate=False` rewriting and triggers eager powers; IEEE non-finite comparisons can otherwise falsely verify a number. No JSON field or dependency changes. | codex |
| 2026-10-09 | Template children are `<template id>-<part>` with `group` = template id; `highlight`/`mark_wrong`/`erase` may target a group | Lets the AI erase or circle a whole template ("the field lines") while slider binds still name a concrete primitive | claude (approved by founder) |
| 2026-10-09 | `step` SSE event carries `audio_url: null` when TTS fails | One TTS hiccup should not end the lesson; the renderer times drawing without audio | claude (approved by founder) |
| 2026-10-09 | `axes_plot` is sampled server-side into a `curve`; bare `plot` is left undrawable for now | The browser cannot run SymPy and `plot` has no y-range | claude (approved by founder) |
| 2026-10-09 | Teaching rules enforced in validation: `say` ≤ 30 words, ≤ 4 steps without a checkpoint (summary exempt), `extra="forbid"` | Invalid AI output fails early and the Phase 1b retry gets a precise error | claude |
| 2026-10-09 | Calc/plot expressions: allow-list check, then SymPy parses with `evaluate=False`, then our own float evaluator walks the tree (`app/lesson/safe_expr.py`) | SymPy's parser calls `eval`, and letting SymPy evaluate untrusted input hangs on `9^9^9^9`; floats overflow instantly instead | claude |
| 2026-10-09 | Dep (server): `sympy` | Calc verification and plot sampling (AGENTS §3) | claude |
| 2026-10-09 | Dep (server): `edge-tts` | Default TTS provider (founder decision 2026-10-08) | claude |
| 2026-10-09 | SSE via FastAPI's built-in `fastapi.sse.EventSourceResponse` | No extra dependency; typed `ServerSentEvent` | claude |
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
