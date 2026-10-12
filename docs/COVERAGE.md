# Coverage plan — from "Gauss's law" to "any physics problem"

Gauss's law is the golden test, not the limit. Scribbly must handle any school or
university physics problem. This file is the plan for getting there and for
measuring it. Phases referenced here are in `docs/SPEC.md`.

## 1. Where we are weak (and why)
| Risk | Why it happens | Fix (section) |
|---|---|---|
| Objects in wrong places, labels overlapping | LLMs are bad at raw pixel coordinates | §2 grid + layout engine |
| Wrong physics in diagram-heavy problems | Vision models still miss many diagram problems | §4 eval bank, §5 visual QA |
| Messy drawings for common scenes | Free-hand primitives every time | §3 template library |
| No 3D (solenoid, rotation, fields in space) | Renderer is 2D only | §6 3D subset |
| We do not know which topics are bad | No measurement | §4 eval bank + topic report |

## 2. Grid coordinates + layout engine  (Phase 1b)
- The AI does **not** write pixels. It writes positions in **grid cells**: the
  1600×1000 canvas is a 16×10 grid of 100-px cells; positions are `[col, row]`
  floats (e.g. `[7.5, 4]`). The server converts to pixels. (Grid-based drawing
  is what made MIT's SketchAgent work with off-the-shelf LLMs.)
- Labels have no fixed position: the AI gives the target and a preferred side
  (`label_side: "above" | "below" | "left" | "right" | "auto"`). The server
  places them and moves them until no label overlaps another label or a stroke.
- After expansion, the server checks every step: nothing outside the canvas,
  no overlapping bounding boxes between unrelated primitives. Problems are fixed
  automatically when possible (nudge, shrink text); otherwise the step is
  regenerated once with the list of problems.

## 3. Template library  (grow from Phase 1a to ~40 by Phase 7)
Templates are drawn by code, so they are always correct and tidy. The AI only
fills parameters (angle, masses, labels). Priority order:

- **Mechanics:** incline_block ✔, free_body ✔, pulley_atwood, projectile,
  circular_motion, pendulum, spring_mass, collision_1d, lever_torque, rolling_body
- **Kinematics:** axes_plot ✔, xt_graph, vt_graph, at_graph
- **Electrostatics:** point_charge ✔, radial_field_lines ✔, dipole_field,
  gaussian_sphere ✔, gaussian_cylinder, charged_plane ✔, parallel_plate_capacitor
- **Circuits:** circuit_series, circuit_parallel, rc_circuit, kirchhoff_loop
- **Magnetism (2D views):** wire_field_circles, solenoid_cross_section,
  lorentz_force (dots/crosses for B), moving_rod_emf
- **Waves & optics:** sine_wave, standing_wave, refraction_snell,
  ray_lens_converging, ray_lens_diverging, ray_mirror, double_slit
- **Thermodynamics:** pv_diagram, carnot_cycle, gas_piston
- **Modern:** energy_levels, photoelectric

✔ = in Phase 1a. Each template: unit test + a fixture lesson that uses it.

## 4. Eval bank  (start in Phase 1b with 30 problems, grow to 200)
`tests/eval/problems.yaml`, one entry per problem:
```yaml
- id: mech-incline-012
  topic: mechanics/incline
  level: university          # simple | university | exam
  input: "A 2 kg block slides down a 30° incline, μk = 0.2. Find a."
  expected:
    - { name: a, value: 3.21, unit: m/s**2, rel_tol: 0.02 }
  must_draw: [incline_block, free_body]   # template or primitive types
  source: "own"                              # own | textbook (no copyrighted text)
```
Runner: `uv run python -m scripts.eval [--topic mechanics] [--limit 10]`.
For every problem it records:
1. schema valid (yes/no) 2. numbers correct vs `expected` 3. required drawings
present 4. layout problems count (§2) 5. visual QA score (§5, when available)
6. time to first step 7. cost in USD.
Report: `docs/eval/YYYY-MM-DD.md` with a table per topic (pass rate, avg cost,
avg latency) and the list of failures.
Grading v4 requires explicit component/oriented quantity and frame metadata for
direction matches, and rejects unreadable expected directions. An expected zero has
empty physical direction; its component calc still declares its reference convention.
This does not check result-direction claims in narration or arrows; those remain
part of the Phase 3 visual QA loop. Older scores are not equivalent to v4 scores.
**Rule:** a change to the lesson prompt, models or templates may not lower the
overall pass rate or any topic's pass rate by more than 5 points. Codex checks
this in review.

Target before the university pilot: ≥ 90 % numbers correct, ≥ 85 % overall pass
on mechanics, electrostatics, circuits; every topic in §3 has ≥ 5 problems.

## 5. Visual QA loop  (Phase 3, after the renderer exists)
Render each finished step to PNG on the server (headless Chromium via
Playwright, reusing the web renderer). Send the PNG + the narration to
`FAST_MODEL` with a short checklist: overlaps, unreadable labels, drawing does
not match what is said, wrong direction of a vector/force. Score 0–5 and a list
of issues. Score < 4 → regenerate that step once. Also used by the eval runner.
Must stay cheap: only the changed step is checked, image ≤ 800 px wide.

## 6. 3D subset  (Phase 7)
three.js scene inside the board for a small set: 3D axes, 3D vectors, coil /
solenoid with field lines, rotating disk/rod, sphere/cylinder Gaussian surfaces
in perspective. Camera can be dragged; narration still drives the build-up.
Only used when a 2D view really cannot show the idea.

## 7. "Bad lesson" feedback  (Phase 3)
A button on every lesson: "This was wrong / confusing" + optional note. Saves
input, lesson JSON and note locally. `uv run python -m scripts.feedback_to_eval`
turns marked lessons into draft eval cases for the founder to confirm.
