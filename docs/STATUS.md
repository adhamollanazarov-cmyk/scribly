# Status

Update this file at the end of every task (newest entry on top, 3–8 lines).

## 2026-10-13 — claude — Merge leftovers, icons, mascot description (`claude/mascot`)

**Done:** Removed the three merge markers in `docs/DECISIONS.md` (every library and Phase 5 entry kept) and the stray `HEAD` / `claude/phase5` lines in this file. An uncommitted working-tree edit had deleted the six Phase 5 DECISIONS rows along with the markers; it was backed up and replaced by this resolution. `desktop/scripts/make_icons.py` now draws Scribbly's head from the new art (round body, pencil tip, eyes with two highlights, cheeks, smile; same colors as `scribbly.css`); the 16 px tray icon drops the small details. `desktop/resources/*.png` regenerated. AGENTS.md §5, `docs/SPEC.md` and `docs/brand/README.md` describe the pencil-tip character.
**Checks:** MOCK_AI=1, no API calls: 714 pytest; ruff lint/format; mypy app (29) + scripts (5). Desktop: 13 Vitest; ESLint+tsc; Prettier; Electron smoke 1/1. Icon script: ruff + mypy clean. Web code unchanged since the polish entry below.
**Found issues:** none new.
**Next:** Human merges `claude/mascot`; Antigravity checks the tray icon on a light and a dark taskbar.

## 2026-10-13 — claude — Scribbly polish + squash-and-stretch (`claude/mascot`)

**Done:** Redrew the art closer to `docs/brand/scribbly-sheet.png`: round, slightly larger body under the pencil cone (measured from the sheet), short arms with mitten hands (thumb; relaxed paw when hanging, fist around the marker, pointing and thumbs-up variants), stubby rounded legs, bigger eyes with two highlights. Squash-and-stretch: pop-in stretches, lands squashed and wobbles; flight squashes to take off and stretches; landing squash on the first pose after a flight (`data-land`); happy jump crouches, stretches, squashes. Every keyframe segment is eased, and pose tilts ease too. Body-below shift 60 → 84 so the mirrored drawing arm no longer crosses the face. All 11 poses + body-below + animation frames rendered in Chromium next to the sheet.
**Checks:** Web: 216 Vitest (+6: two highlights per eye, mitten thumbs, landing only after a flight); ESLint+tsc; Prettier; Playwright 7/8 with `--workers=1` (incl. `gauss-lesson.spec.ts`). The 8th, `phase2-fixes` "handwriting uses loaded font advances", failed in the full run (9.68 px) and passes alone (4/4), the known order-dependent issue below.
**Found issues:** low — no automated check that the CSS durations match `APPEAR_MS`/`FLY_MS`/`DISAPPEAR_MS`: Vitest does not load CSS (`?raw` comes back empty), so they are kept in sync by hand.
**Next:** Antigravity QA of the motion in the overlay (appear, flight + landing) and the new hands at overlay scale 1.4.

## 2026-10-12 — claude — New Scribbly art (`claude/mascot`)

**Done:** Recreated `docs/brand/scribbly-sheet.png` as a layered SVG in `web/src/mascot/Scribbly.tsx` (legs, body, pencil-tip wood/graphite, eyes, eyelids, cheeks, mouth shapes, free arm, marker arm, marker, effects) and replaced the purple character (no flag). New `mascot/pose.ts` maps every state to a pose; the existing state machines are untouched. Blinks in idle, lip-syncs while narrating, marker tip sits on the pen while drawing/pointing, marker always in the same hand, soft `feDropShadow` for white pages. Overlay headroom 110 → 130 px for the taller art. `docs/brand/README.md` updated (pose table, rules, contract).
**Checks:** MOCK_AI=1, no API calls: 714 pytest; ruff lint/format; mypy app (29) + scripts (5); schema/streams not regenerated (no server change). Web: 210 Vitest (+31: 11 state→pose cases, mouth, marker hand/tip, drop shadow, blink); ESLint+tsc; Prettier; Playwright 8/8 with `--workers=1` (incl. `gauss-lesson.spec.ts`). Desktop: 13 Vitest, ESLint+tsc, Prettier, Electron smoke 1/1. All 11 poses rendered in Chromium and compared with the sheet.
**Found issues:** low — `docs/DECISIONS.md` still contains unresolved merge markers (`<<<<<<< HEAD` … `>>>>>>> claude/phase5`) and `docs/STATUS.md` has stray `HEAD` / `claude/phase5` lines from the library + Phase 5 merges. low — tray/app icons (`desktop/scripts/make_icons.py`) still draw the purple character. low — AGENTS.md §5 and `docs/SPEC.md` still describe Scribbly as "round purple, round glasses".
**Next:** Antigravity QA of the new poses in the overlay and on the board (light and dark); redraw the icons from the sheet.

## 2026-10-12 — codex — Offline physics library (`codex/library`)

**Done:** 20 authored JSON worked examples with English narration and Uzbek subtitles; `app.library.find_library_lesson(text) -> Lesson | None` validates/compiles through the production step checker, with no API, TTS or route wiring. Files retain draft placeholders and sign/frame metadata; examples keep their own stated givens. Work isolated in `.worktrees/library`; Phase 5 areas and mock pipeline untouched.
**Topics:** 1D kinematics; projectile motion; Newton’s second law on an incline with friction; circular motion; work–energy; momentum and 1D collision; torque and rotational equilibrium; spring SHM; simple pendulum; Coulomb’s law; point-charge field; Gauss line charge; Gauss plane; electric potential and parallel-plate capacitor; Kirchhoff two-loop circuit; magnetic force on a moving charge; Faraday moving rod; string wave speed; Snell’s law; thin converging lens.
**Checks:** 698 pytest (97 library cases, independently recomputing all 37 numeric answers in plain Python); Ruff lint/format; mypy app/scripts; 117 Vitest; ESLint/tsc; Prettier; 8 Playwright including Gauss audio/drawing playback. Schema/streams unchanged on regeneration. All 20 rendered boards visually reviewed; no clipped formulas/legends. MOCK_AI=1; no Anthropic calls or real TTS. Playwright passed cleanly after rerunning outside the sandbox to resolve a test-server teardown hang.
**Next:** Human merges; Phase 5 calls the lookup and displays the returned example’s source problem. Lookup is topic matching, not arbitrary problem solving; ambiguous multi-topic requests return None.
**Found issues:** None new; existing Phase 1c/3 limitations remain.

## 2026-10-12 — claude — Phase 5 overlay MVP (`claude/phase5`)

**Done:** `desktop/` Electron tray app (starts hidden): Ctrl+Shift+Space → dimmed selector on every display → drag → only that region is captured (in memory, ≤1600 px) → `POST /explain-region` (new; mock mode streams the Gauss fixture with `X-Scribbly-Demo: 1`, live mode errors until Phase 4) → lesson drawn over the region in a transparent, always-on-top, click-through window; Esc closes. Overlay UI is a second Vite entry `web/overlay.html` reusing the player/board/Scribbly/subtitles/checkpoint card: Scribbly + drawing + EN/UZ subtitles + "Demo lesson" notice + pill (pause/resume, replay, speed, close), no step list. Scribbly motion state machine (appear, fly, draw, talk, point, listen, think, happy, encourage, idle, disappear) with new poses, all art still in `Scribbly.tsx` (`docs/brand/README.md`). Tray: voice, speed, subtitle line, launch at login (off by default), quit. Security: contextIsolation, no nodeIntegration, sandboxed esbuild-bundled preload with a 4-call API, CSP via `app://scribbly`, navigation/window.open/permissions denied. electron-builder NSIS config + PowerShell README.
**Checks:** PowerShell-compatible, MOCK_AI=1, no Anthropic calls: 617 pytest (+17 `/explain-region`); ruff lint/format; mypy app (28) + scripts (5); schema/streams regenerate unchanged. Web: 179 Vitest (+62: geometry at 100/125/150 %, motion machine, overlay, settings, `streamEvents`); ESLint+tsc; Prettier; Playwright 7/8 with `--workers=1`. Desktop: 13 Vitest, ESLint+tsc, Prettier, Playwright-Electron smoke 1/1. Live on this PC (1 monitor, 125 %): real mock server, board exactly over the dragged rectangle, narration through the `app://` proxy (206 range), EN+UZ subtitles, Esc closes. Installer: `desktop/release/Scribbly Setup 0.1.0.exe` (NSIS, x64, 108 MB) built; the same Electron smoke test passes against the packaged `win-unpacked/Scribbly.exe` (resources paths, `app://` renderer root, tray icon).
**Found issues:** low — the installer is not code-signed, so Windows SmartScreen will warn on first run. low (pre-existing) — `phase2-fixes.spec.ts` "handwriting uses loaded font advances" fails in the full web Playwright run (mascot 9.7 px from the pen) but passes alone; it also fails on unmodified `main` (16 px), so it is order/timing dependent, not caused by Phase 5. low — the installer does not bundle the Python server yet (README: start it separately). low — only 125 % scaling and a single monitor exist on this machine: 100/150 % and a second monitor are covered by unit tests, not live. low — `globalShortcut('Escape')` is taken from other apps while a lesson is open (by design, see DECISIONS). low — `npm install` did not fetch the Electron binary on first try (network); `node node_modules/electron/install.js` fixed it.
**Next:** Antigravity QA of the overlay on real apps (ChatGPT, PDF, slides) and on a second monitor at 150 %; Codex review (security of the protocol proxy and IPC); then the lesson library.

## 2026-10-12 — founder — roadmap change after trying Phase 2

**Done:** Phase 2 integrated and merged. Founder feedback: lesson is fine; must run on top
of any app, not a website; no step list for users; new character with several movements.
**Next:** Phase 5 overlay MVP (PROMPTS.md), then the lesson library. Eval for 1b.2 and the
Phase 1c eval still wait for API credit.
**Found issues:** none new.

## 2026-10-12 — claude — Phase 2 integration (`claude/phase2-integrate`)

**Done:** Merged `codex/phase2-review` (3 highs: SSE terminal frame, media error/stall fallback, zero-target checkpoints) + `claude/phase2-review` (5 fixes: TTS retry + no-audio notice, circuit layout, measured font bounds + super/subscripts, lazy board/KaTeX chunks, server-sampled plots) + `ag/phase2-qa` (QA notes). Only docs conflicted; every entry kept, no fix overlapped. Then fixed the open Codex findings: M1 background clock catch-up, M2 dense/late stroke budget, M3 ticker active flag, M4 abort request on unmount, M5 hidden per-step board transcript (MathML, `aria-details`), L2 visible radio focus. The 3 strict xfail probes are normal tests now. L1 bundle already fixed by `claude/phase2-review`.
**Checks:** PowerShell-compatible, MOCK_AI=1, no API/TTS calls: 601 pytest; ruff lint/format; mypy app (27) + scripts (5); schema/streams regenerate unchanged; 117 Vitest (was 108 + 3 xfail); ESLint+tsc; Prettier; Playwright 8/8 with `--workers=1`, Gauss 4/4 repeated.
**Found issues:** low — `gauss-lesson.spec.ts` is flaky under parallel workers (2/6 fail on the pre-fix merge too): at 1.5× step `s1` lasts ~1.4 s and a loaded machine misses the `data-step="s1"`/subtitle assertions. Needs a non-transient check (e.g. record step changes in-page). M5 still needs manual screen-reader QA. AG items still open: checkpoint card below the fold at 1280×720, intro `foreignObject` at negative y, field arrows near surface labels (its superscript-minus finding is fixed by `claude/phase2-review`).
**Next:** Human merges `claude/phase2-integrate`; Codex reviews the M1–M5/L2 fixes; Phase 3 raise-hand.

## 2026-10-12 — codex — Phase 2 review (`codex/phase2-review`)

**Done:** Reviewed `claude/phase2` (`56f0316`) against `main` (`0c8e101`). Fixed three highs: incomplete SSE silently waiting forever, post-metadata media errors/permanent stalls freezing playback, and zero checkpoints accepting nonzero physical answers. Added 16 passing unit regressions, one browser regression and three strict expected-failure probes for unfixed mediums. Full severity list: `docs/reviews/2026-10-12-phase2.md`.
**Checks:** PowerShell 5.1, fake/mock providers only: 580 pytest; Ruff lint/format; mypy app+scripts; schema and streams unchanged on regeneration; 102 Vitest passed + 3 expected failures; ESLint+tsc; Prettier; 4 Chromium tests (including Gauss audio/drawing completion) using an isolated server on port 5187. Production build passes with the known 548.59 kB JS warning. No real API/TTS calls, captured media or new dependencies.
**Found issues:** Mediums left open: background-tab clock catch-up, dense/late stroke timing, animation-frame cleanup, request cleanup on unmount, and an accessible board transcript. Lows: oversized bundle and invisible radio keyboard focus. Prior Phase 2 STATUS issues remain on this base; the earlier five-issue follow-up is separately committed as `aa48ab3` on `claude/phase2-review`.
**Known limitation:** Prose/arrows contradicting metadata remains for the Phase 3 visual QA loop; numeric verification alone does not establish visual/narrative agreement.
**Next:** Human merges the high fixes; follow up on listed mediums/lows and remove the matching `.fails` markers when fixed. Live reliability, latency and provider cost were not measured.

## 2026-10-12 — codex — Phase 2 five issue fixes (`claude/phase2-review`)

**Done:** Fixed all five issues from the Phase 2 entry: bounded edge-tts retry + readable no-audio fallback; non-overlapping/in-bounds circuit fixture; loaded-font bounds/pen advances + superscript glyphs; lazy board/KaTeX chunks; safe server-side bare-plot sampling. Plot y ranges are now required; docs, prompt, models, generated schema, TypeScript and golden fixtures/streams updated together. Details: `docs/reviews/2026-10-12-phase2-fixes.md`.
**Checks:** PowerShell 5.1, fake/mock providers only: 601 pytest; Ruff lint/format; mypy app+scripts; schema/stream regeneration; 92 Vitest; ESLint+tsc; Prettier; 6 Chromium tests including Gauss audio/drawing completion, circuit layout, font metrics and bare plots. Production build passes (largest JS chunk 258.92 kB). No real API/TTS calls or saved captures; no dependencies added.
**Found issues / known limitation:** “Prose/arrows contradict metadata” remains for the Phase 3 visual QA loop; named/projected geometry also needs visual review. Existing quantity/direction, ideal-emf battery and script-typing fixes are inherited unchanged. Live TTS reliability/latency and general generated-layout quality were not measured; inherited Phase 1b findings remain open.
**Next:** Human merges; validate live voice on the founder's network when authorized. Phase 3 compares rendered directions/narration and adds interruption/re-explanation; Phase 1c still owns prefetch and general layout planning.

## 2026-10-12 — antigravity — Phase 2 browser QA & Gauss lesson review (`ag/phase2-qa`)

**Done:** Browser QA of Gauss's law lesson on Chromium (mock server + cached edge-tts audio) across speeds 0.5×, 1.0×, 1.5×. Verified drawing & audio synchronization (all 7 steps start/end with narration), mascot pen tracking (holds pencil at pen tip, looks at lead, moves mouth only when speaking, blinks), KaTeX/handwriting layout readability, bilingual subtitles (EN + UZ matching every step), mid-step pause/resume, and checkpoint wrong-then-right flow. Measured time from click to first stroke: 1.22 s (1.5×), 1.48 s (1.0×), 3.06 s (0.5×) — target < 3 s met. Captured 14 screenshots into `screenshots/`.
**Checks:** PowerShell 5.1, Chromium Playwright E2E: `gauss-lesson.spec.ts` passes; ESLint + tsc, Prettier pass. Mock server `/health` ok.
**Found issues:** med — checkpoint card extends below viewport fold on standard 1280×720 / 768p displays because the board is placed under the form (`qa-checkpoint-wrong.png`, `qa-0.5x-step5-checkpoint.png`); needs auto-scroll into view or viewport-aware layout. low — Caveat handwriting font lacks unicode glyphs `⁻` (superscript minus) and `₀` (subscript zero) in step 6 `ε₀ = 8.85 × 10⁻¹² C²/(N·m²)` (`qa-0.5x-final.png`). low — `HtmlOnBoard` foreignObject container for `sym-q` starts at negative y (-48) because room (4 × size = 128) exceeds baseline offset y=80 (`qa-visual-inspect.png`), though text content itself renders inside viewBox. low — radial field arrows pass very close to dashed surface labels ("Gaussian surface", "bigger surface") (`qa-1.0x-final.png`). Phase 3 note — voice/text interruption ("raise hand") and re-explaining branch generation are not yet implemented (deferred to Phase 3).
**Next:** Claude implements Phase 1c layout improvements and Phase 3 raise-hand / branch re-explain; Codex review.

## 2026-10-12 — claude — Phase 2 board renderer + mascot (`claude/phase2`)

**Done:** Web plays lessons: every primitive as animated rough.js/KaTeX/Caveat SVG with semantic color tokens (light/dark). Audio and strokes share one narration clock, fitted to audio length at speed 0.5–1.5×. Step 1 starts while later steps stream; the problem and its givens are written at once while generating. Scribbly is a separate SVG component with 7 states: it blinks, follows the pen and lip-syncs. Controls: play/pause, restart, speed, step list, replay step, EN + UZ/RU subtitles, checkpoint card. Server: mock mode picks the fixture by source text; `shared/streams` (new `gen_streams`) feeds web tests. Added golden fixture `circ_series` (the only 2026-10-10 eval lesson with all calcs verified).
**Checks:** PowerShell 5.1, MOCK_AI=1: 580 pytest, ruff, format, mypy app+scripts, schema/streams unchanged on regeneration; 86 Vitest, ESLint+tsc, Prettier, 3 Playwright (incl. `gauss-lesson.spec.ts`: all 7 steps audio ended + drawn, checkpoint, no console errors). Live, mock server + real edge-tts: first step playing 2.1–2.3 s after click, both sample lessons played through with no console errors. No Anthropic API calls.
**Eval:** Phase 1b.2 eval still pending until API credit is added (see the 1b.2 entry).
**Next:** Antigravity QA of drawing/voice sync and the mascot; Phase 1c grid layout + TTS prefetch/retry; Phase 3 raise hand and re-explain branches.
**Found issues:** med — edge-tts failed for 2/7 Gauss steps and 1/9 series steps live; those steps play silently on the word-count clock (server retry belongs to 1c). med — `circ_series` places legend rows and formulas on top of each other, and `req-eq` runs past x = 1600 (AI layout, 1c). low — text/formula widths are estimates, so highlight loops and the pen tip are approximate; Caveat lacks ⁻ (fallback glyph). low — web bundle > 500 kB (KaTeX); code-split later. low — `plot` is still not drawn (skipped).

## 2026-10-12 — codex — Phase 1b.2 medium/low fixes (`codex/phase1b2-review`)

**Done:** Fixed M1–M6 and L1–L2 from `docs/reviews/2026-10-12-phase1b2.md`: required quantity/frame metadata and conditional `positive` (including zero), relevant convention drawings before use, grounded numeric exemptions, spaced unit macros, fail-closed expected directions, ideal-emf battery wording, script typing and finite direction inputs. Prompt/docs/saved draft metadata updated together; renderer contract/schema unchanged.
**Checks:** PowerShell 5.1, mock/fake providers: 567 pytest (76 follow-up cases), Ruff lint/format, mypy app (26 files) and scripts (4), schema regeneration passed; 5 Vitest, ESLint+tsc, Prettier and 1 Chromium smoke test passed. No real API/TTS calls; live pass rate, latency and fix cost were not measured.
**Found issues / known limitation:** M7, “prose/arrows contradict metadata”, remains intentionally unfixed for the Phase 3 visual QA loop: numeric direction metadata does not prove narration, result labels or arrows agree. Named/projected geometry also needs visual review. Existing Phase 2 Gauss audio/drawing playback coverage and inherited Phase 1b findings remain open.
**Next:** Human merges; Phase 3 visual QA compares rendered steps with narration. Future API evals use grading v4 (older scores are not equivalent); no historical reports were re-scored. Added `types-PyYAML` with a dependency reason and script mypy to §6.

## 2026-10-12 — codex — Phase 1b.2 review (`codex/phase1b2-review`)

**Done:** Reviewed `claude/phase1b2` (`323f3b7`) against `main` (`33b1886`). Fixed high: zero-tolerance bound falsely accepted wrong answers and erased real residuals; ambiguous calculations now use bounded higher-precision/stability rechecks. Independently recomputed all 20 hard problems / 69 answers; targets agree (battery-power wording needs clarification). Evidence and severity list: `docs/reviews/2026-10-12-phase1b2.md` and companion JSON.
**Checks:** PowerShell 5.1, mock/fake providers: 492 pytest (30 added), Ruff lint/format, mypy app, unchanged regenerated schema; 5 Vitest, ESLint+tsc, Prettier and 1 Chromium smoke test passed. No real API/TTS calls; declared already-locked mpmath directly, with no version changes.
**Found issues:** Mediums remain: empty direction metadata, unrelated/late convention drawings, expression-literal provenance exemptions, unit/symbol ambiguity, invalid expected directions failing open, battery-power wording and unchecked presentation directions. Low: four script mypy errors (one PyYAML stub + three `reasons` typing errors), nonfinite direction helper inputs. Existing Phase 2 playback gap remains.
**Next:** Human merges; follow up on medium/low findings. Require `positive` for explicitly typed direction-bearing components/oriented quantities (including zero), while scalars/magnitudes retain empty direction; proposal only, not applied here.

## 2026-10-12 — claude — Phase 1b.2 signs, lint, zero tolerance, eval bank v1 (`claude/phase1b2`)

**Done:** One sign convention per lesson. Calc drafts carry `positive` (`+x`, `A->B`, `down the slope`…) in the draft and ledger only; the lesson contract is unchanged. A new `sign` lint rejects unreadable, opposite or undrawn conventions, and the prompt has a sign-convention section. Lint: `\Omega`/`\mu` after a number are units; 0.5/0.25 exempt only inside LaTeX; numbers in calc `expr` count as inputs. Verify: absolute tolerance from a rounding-error bound, so true zeros store as 0; no "-0.00". Eval grading v3: `direction` on expected numbers, so circ-kirchhoff is checked automatically. Bank v1 adds +20 `hard` problems (50 total).
**Checks:** PowerShell 5.1, MOCK_AI=1: 462 pytest (59 new), ruff, format, mypy app; shared schema unchanged. Web (bash): 5 Vitest, ESLint+tsc, Prettier, 1 Chromium Playwright test passed (web untouched).
**Eval: not run.** The API credit is exhausted: all 10 `--source hard --limit 10` requests returned 400 "credit balance is too low" ($0.00 spent; empty report deleted). Offline replay of the saved 2026-10-10 circ-kirchhoff lesson under the new code: I1/I2/I3 now fail on direction (no convention declared); the KCL check `c7` now verifies (it was −8.9e-16 vs 0, which left its step unverified); the summary's hand-written, wrong "0.25 amperes" is now flagged.
**Next:** Add API credit, then `uv run python -m scripts.eval --source hard --limit 10 --max-cost 3`, then the full bank (~$5–7). Watch how many extra paid fix calls the new `sign` lint triggers.
**Found issues:** low — the sign lint only acts when the model fills `positive`; a vector left with `""` passes lint, and only the eval `direction` check catches it. low — direction claims in prose (summary) are still not machine-checked. low — `uv run mypy scripts` shows 4 pre-existing errors in `scripts/eval.py` (`reasons` used as both list and Counter); §6 checks only `app`.

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
**Checks:** PowerShell 5.1, MOCK*AI=1: 185 pytest passed, 5 strict xfails documenting unfixed medium findings; ruff lint/format, mypy, unchanged regenerated schema; 5 Vitest, ESLint+tsc, Prettier, 1 Chromium smoke test passed. Tracked credential/media scan passed; no real API/TTS calls or contract/dependency changes.
**Found issues:** med — raw template/exception content in logs; supplied warning suppresses spoken disclaimer; `from*` accepted contrary to shared schema; intermediate summaries bypass checkpoint spacing; non-finite drawing coordinates serialize as null. low — Gauss playback E2E is absent while the web remains a Phase 2 placeholder.
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

## **Done:**

## **Next:**

## **Found issues:**
