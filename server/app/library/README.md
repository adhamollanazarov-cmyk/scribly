# Offline physics library

`find_library_lesson(text) -> Lesson | None` matches English topic phrases (and each
lesson's title) with case, punctuation and word-boundary normalization. It returns
`None` for unknown or ambiguous multi-topic requests, for text that contains a number
with a unit (a problem with its own data), and when a topic's negative keywords appear
(`"elastic"`, `"cliff"`, `"conical"`, `"cage"`…: neighbouring physics the example does not
cover; see `docs/reviews/library.md` H1). Each call returns a fresh lesson with a stable
UUID.

These are **worked examples with their own stated givens**, not solutions to
arbitrary numbers in the lookup text. Display `lesson.source.text` with the lesson
so the student can see the problem being solved.

Each JSON file contains `source` plus the existing generation-draft fields
(`title`, `level`, `steps`). The draft representation preserves result placeholders,
quantity kinds, reference frames and drawn sign conventions. It uses the existing
schema described in `docs/LESSON_SCHEMA.md`; no renderer contract was changed.
The loader validates the source/draft, runs `check_step` and `commit` for every
step, rejects **all** lint violations, and validates the final `Lesson`. This runs
Pydantic validation, teaching and sign lint, template/plot expansion, reference
checks and SymPy verification without any AI, TTS or network access.

English narration and Uzbek subtitles accompany every step; checkpoint questions are
translated in `subtitles.uz` (choices stay English: translated choices need a schema
change). Russian is not written yet, so `ru` is `""` in the files and `null` in the
lesson. Every lesson has two checkpoints:
- a **concept** question about a changed situation or a common misconception, with 3–4
  choices and the answer at varying positions, never stated by an earlier step;
- a **prediction**: the checkpoint step holds the calc, the student predicts the result,
  and the next step reveals it. Its re-explain hint is a different approach, not a copy. Template scenes are used when implemented; a cylinder,
spring, pendulum, circuit and lens use primitives because those templates are not
yet implemented. Drawings are schematic; coordinates are not physical data.

`server/tests/test_library.py` independently recomputes all 37 numeric answers
with fixed problem inputs and Python arithmetic/`math`, without using the lesson
expressions or SymPy. Circuit loop equations, power balance, momentum and torque
balance add cross-checks. Tests also cover lookup, isolation, full compilation,
subtitles, checkpoint answers and rejection of damaged authored content.

## Editing the lessons
The JSON files are the source. The generator that first wrote them was never committed
and is gone (`docs/reviews/library.md` M5), so edit the files directly; they are
formatted as `json.dumps(raw, ensure_ascii=False, indent=2)` plus a newline. Loading runs
the full lint and SymPy pipeline, and `tests/test_library.py` enforces the checkpoint
rules above, so a broken edit fails `uv run pytest`.
