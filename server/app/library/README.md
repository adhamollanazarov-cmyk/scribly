# Offline physics library

`find_library_lesson(text) -> Lesson | None` matches English topic phrases with
case, punctuation and word-boundary normalization. Unknown or ambiguous
multi-topic requests return `None`. Each call returns a fresh lesson with a stable
UUID. Import from `app.library`; route integration belongs to Phase 5.

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

English narration and Uzbek subtitles accompany every step. The first checkpoint
tests a concept and supplies a different explanation hint; the second checks a
verified numeric result. Template scenes are used when implemented; a cylinder,
spring, pendulum, circuit and lens use primitives because those templates are not
yet implemented. Drawings are schematic; coordinates are not physical data.

`server/tests/test_library.py` independently recomputes all 37 numeric answers
with fixed problem inputs and Python arithmetic/`math`, without using the lesson
expressions or SymPy. Circuit loop equations, power balance, momentum and torque
balance add cross-checks. Tests also cover lookup, isolation, full compilation,
subtitles, checkpoint answers and rejection of damaged authored content.
