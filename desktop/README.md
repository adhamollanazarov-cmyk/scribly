# Scribbly desktop (Windows overlay)

A tray app. Press **Ctrl+Shift+Space**, drag over anything on screen (a ChatGPT answer, a
PDF, a slide), and Scribbly draws and explains a lesson on top of it.

Until Phase 4 (vision) the server answers every region with a **demo lesson** from the
fixture library; the overlay says so in the subtitles.

## How it fits together

- `desktop/` holds only Electron's main process and preload (`src/main`, `src/preload`),
  bundled by esbuild into `dist/main.js` and `dist/preload.js`.
- The overlay page itself is `web/overlay.html` (`web/src/overlay/`): it reuses the web
  player, board, Scribbly and subtitles. The packaged app serves the built page from
  `app://scribbly/` and proxies `/explain-region` and `/audio/*` to the server.
- The page talks to Electron only through `window.scribbly` (four calls, see
  `web/src/overlay/bridge.ts`).
- Privacy: nothing is captured without the hotkey. Only the selected region is cut out of
  the capture, kept in memory, sent once to the server, and never written to disk.

## Run it (PowerShell, from the repo root)

Start the server in mock mode (no API key needed):

```
cd server
$env:MOCK_AI="1"
uv run fastapi dev app/main.py
```

In a second window:

```
cd desktop
npm install
npm start
```

`npm start` builds `web/` and the Electron code, then starts the tray app. Press
Ctrl+Shift+Space, drag over a region, and the demo lesson plays there.

- Esc closes the lesson (or cancels the selection).
- The pill under the board: pause/resume, replay step, speed, close.
- Click Scribbly to pause or resume.
- Tray icon menu: Settings (voice, speed, second subtitle line, launch at login), Quit.
  Launch at login is off by default and only applies to the installed app.

Server elsewhere: `$env:SCRIBBLY_SERVER="http://127.0.0.1:8000"` (the default).

### UI work with hot reload

Run the server as above, then `cd web` and `npm run dev`. Either open
http://localhost:5173/overlay.html in a browser (a demo bridge starts a lesson; add
`?select` for the selector), or run Electron against Vite:

```
cd desktop
$env:SCRIBBLY_RENDERER_URL="http://localhost:5173"
npm run dev
```

## Checks

```
cd desktop
npm test
npm run lint
npm run format:check
npm run e2e
```

`npm run e2e` builds everything and runs the Playwright-Electron smoke test against a stub
server (no Python server needed). It drives a real desktop capture, so run it on an
unlocked Windows session.

## Windows installer

```
cd desktop
npm run dist
```

The NSIS installer appears in `desktop\release\`. The installer does not include the
Python server yet; start it as above.
