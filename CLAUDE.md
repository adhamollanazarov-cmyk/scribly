@AGENTS.md

# Claude Code specifics

The shared rules above (AGENTS.md) are the source of truth. This file adds only
Claude Code habits.

- Start every non-trivial task in plan mode: restate the goal, list files you will
  touch, name the tests you will add. Wait for approval if the plan changes the
  lesson schema or adds a dependency.
- Work in small, reviewable commits on a `claude/<task>` branch.
- Run the checks in AGENTS.md §6 yourself before saying a task is done, and paste
  the short result (pass/fail counts).
- Use mock mode (`MOCK_AI=1`) for UI work so you do not spend API credits.
- When you write or change the lesson system prompt, test it on these three inputs
  and save the outputs as fixtures if they pass review:
  1. "Explain Gauss's law"
  2. "A point charge of 3 nC sits at the center of a sphere of radius 0.2 m.
     Find the electric flux through the sphere and the field on its surface."
  3. A screenshot of a ChatGPT solution containing one deliberate mistake.
- Prefer editing existing files over creating new ones. Keep functions small.
- If something in AGENTS.md is wrong or outdated, propose the fix in your summary
  instead of silently ignoring it.
- End each task by updating `docs/STATUS.md`.
