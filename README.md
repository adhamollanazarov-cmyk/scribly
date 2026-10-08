# Scribbly

An AI teacher that explains physics by drawing step by step while speaking.
Product spec: `docs/SPEC.md`. Rules for contributors and agents: `AGENTS.md`.

```
server/   FastAPI (Python 3.12) — lessons, TTS, verification
web/      Vite + React + TypeScript — board, mascot, controls
desktop/  Electron overlay (Phase 5)
shared/   generated lesson JSON Schema
docs/     spec, schema, status, decisions
tests/fixtures/lessons/   golden lessons
```

## Prerequisites (Windows 11)

- Python 3.12 and [uv](https://docs.astral.sh/uv/): `winget install astral-sh.uv`
- Node.js 22 or newer: `winget install OpenJS.NodeJS.LTS`
- Git

All commands below are for **Windows PowerShell**, one per line, starting from the
repo root. They also work in bash.

## First-time setup

```powershell
Copy-Item .env.example .env        # then put your key in ANTHROPIC_API_KEY (optional in mock mode)
cd server
uv sync
cd ..\web
npm install
npx playwright install chromium    # browser for end-to-end tests
cd ..
```

## Run

Two terminals:

```powershell
# terminal 1 — server on http://localhost:8000  (health: /health)
cd server
uv run fastapi dev app/main.py
```

```powershell
# terminal 2 — web on http://localhost:5173
cd web
npm run dev
```

### Mock mode (no API key, no credits)

```powershell
$env:MOCK_AI="1"
cd server
uv run fastapi dev app/main.py
```

`$env:MOCK_AI` lasts for the current terminal only. You can also set `MOCK_AI=1` in `.env`.

## Checks (run before saying a task is done)

```powershell
cd server
uv run pytest
uv run ruff check .
uv run ruff format --check .
uv run mypy app
cd ..\web
npm test
npm run lint
npm run format:check
npx playwright test
cd ..
```

Auto-fix formatting: `uv run ruff format .` (server), `npm run format` (web).

## Troubleshooting

- `&&` gives a parse error: Windows PowerShell 5.1 does not support it. Run the commands
  one per line as shown, or install PowerShell 7.
- Playwright says "Executable doesn't exist": run `npx playwright install chromium` in `web/`.
- `npm run dev` fails with "Port 5173 is in use": another dev server is running; close it.
