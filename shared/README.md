# shared

Generated files. Do not edit by hand.

- `lesson.schema.json`: the lesson JSON Schema, built from the Pydantic models in
  `server/app/lesson/models.py` (`uv run python -m scripts.gen_schema`). Added in Phase 1.
- `streams/<fixture>.json`: the SSE events mock mode sends for each golden fixture in
  `tests/fixtures/lessons/` (`uv run python -m scripts.gen_streams`). The web tests replay
  them. Added in Phase 2.
