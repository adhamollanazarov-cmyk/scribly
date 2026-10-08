# Product spec — Scribbly

## 1. Problem
Students now get homework answers from ChatGPT in seconds, but they do not
understand the written solution. Many learners also struggle to picture physics in
their head (fields, flux, forces, vectors). Text answers do not fix that.

## 2. Promise
"Select anything on your screen. A small teacher draws it out and explains it out
loud, step by step, until you actually get it."

## 3. Users
1. **Now:** the founder — university student, physics taught in English, Windows 11
   laptop, struggles with topics like Gauss's law.
2. **Next:** classmates at his university (pilot of ~20 students).
3. **Later:** grades 10–11 and DTM / university-entrance students in Uzbekistan,
   sold through learning centers (B2B) and to parents.

## 4. Competitors and what we take / beat
| Product | What it does well | Our answer |
|---|---|---|
| HeyClicky | On-screen buddy, hotkey, sees screen, points/draws | Same overlay feel, but a real teacher: full step-by-step lessons; Windows first |
| Meta Muse | Cute mascot, agent that acts for you | Not education. We copy nothing; our mascot teaches |
| Gauth Canvas | One continuous board, narrated lessons, pause to ask | Works over the student's own material, not only inside our app; verified math |
| SketchMind | Plans lesson, one idea at a time, checkpoints | Same pedagogy + voice by default + screen overlay |
| Biro | Diagrams, student can edit/draw over board | Same + student drawing gets checked |
| BoardyBoo | Voice, interrupt any time, reads the board | Same interruption model, plus screen overlay |
| Dudely | Draws, talks, checks understanding | Same core + local languages + overlay |

Table stakes (must have, others already do): draw + voice in sync, interrupt and
ask, checkpoints, replay, save lesson.
Differentiators (must win): screen overlay, "explain this AI solution and find its
mistake", verified numbers, Uzbek/Russian subtitles, Windows.

## 5. Features by phase
### Phase 1 — Lesson engine (web)
- Input: topic or problem text. Output: streamed lesson JSON (see LESSON_SCHEMA.md).
- Template library for common physics scenes (expanded server-side, deterministic):
  `point_charge`, `radial_field_lines`, `gaussian_sphere`, `gaussian_cylinder`,
  `charged_plane`, `incline_block`, `free_body`, `spring_mass`, `pendulum`,
  `circuit_series`, `circuit_parallel`, `axes_plot`, `vector_add`.
- TTS per step, cached. Mock mode with golden fixtures.

### Phase 2 — Board renderer + mascot
- Reference for look and feel: `docs/prototype/gauss_lesson_prototype.html`
  (stroke animation, pen-following mascot, subtitles). Rebuild it properly in
  React from the lesson JSON; do not copy its browser speechSynthesis approach.
- Animated hand-drawn strokes, KaTeX formulas, handwriting labels.
- Mascot "Scribbly" (original, same name as the product): round purple body, round glasses, small antenna with orange
  tip, holds a pencil. It walks to the pen tip while drawing, mouth moves while
  audio plays, blinks, idles in a corner when done. States: idle, drawing,
  talking, listening, thinking, happy (correct answer), encouraging (wrong answer).
- Controls: play/pause, restart, speed 0.5–1.5×, subtitles EN + UZ (RU optional),
  step list to jump back, replay a single step.

### Phase 3 — Interaction
- **Raise hand:** hold Space or click "?" → pause audio and drawing → speech to text
  (browser Web Speech API first; Whisper/Deepgram later) → server receives
  {lesson, current step, board primitives, question} → returns a short branch
  (1–3 steps) drawn in a side area → "Back to the lesson" resumes.
- **Checkpoints:** multiple choice or numeric; correct → mascot happy, continue;
  wrong → `reexplain` branch with a different approach; two wrongs → show the
  worked step and move on (never block the student).
- **Interactive scenes:** a step may expose 1–2 sliders (e.g. Gaussian surface
  radius, charge position) so the student can play with the idea.

### Phase 4 — Explain my screenshot + verification
- Paste or upload an image (ChatGPT answer, textbook page, handwritten work).
- Claude vision extracts the problem and the given solution, then builds a lesson
  that walks through it and marks wrong steps (red circle + reason).
- Verification: every numeric result in the lesson is emitted as a `calc` item
  (SymPy expression + expected value + units). Server evaluates; mismatch → one
  regeneration, still wrong → show the warning "I'm not sure about this number".

### Phase 5 — Windows overlay (Electron)
- Global hotkey `Ctrl+Shift+Space` → dim screen → drag to select a region →
  capture only that region.
- Transparent, always-on-top, click-through window; the lesson is drawn **on top of
  the captured region**, mascot walks there. Esc closes. A small floating panel
  holds controls and subtitles.
- Tray icon, launch at login (opt-in), auto-update later.
- Privacy: nothing captured without the hotkey; no screenshot stored by default.

### Phase 6 — Memory, practice, sharing
- Local SQLite: topics studied, mistakes, checkpoint results.
- Next-day review: 2–3 short questions on weak topics (spaced repetition).
- Level switch: "simple words", "university", "exam".
- Export a lesson as video (canvas captureStream + audio → WebM/MP4) and PDF notes.
  Exported videos can feed the founder's YouTube channel.

## 6. Success metrics for the founder pilot
- Founder can explain Gauss's law back after one lesson (self-test 3/3).
- First stroke < 3 s; zero wrong numbers in 20 test problems.
- Pilot: 10 of 20 classmates come back on their own within a week.

## 7. Out of scope for now
Phone app, payments, teacher dashboard, non-physics subjects (chemistry comes
after the physics pilot works).
