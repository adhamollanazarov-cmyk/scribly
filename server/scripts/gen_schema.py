"""Regenerate shared/lesson.schema.json. Run from server/: uv run python -m scripts.gen_schema"""

from app.lesson.schema_export import SCHEMA_PATH, write_schema

if __name__ == "__main__":
    write_schema()
    print(f"wrote {SCHEMA_PATH}")
