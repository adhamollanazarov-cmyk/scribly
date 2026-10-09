"""Render shared/lesson.schema.json from the Pydantic models."""

import json

from app.lesson.models import Lesson
from app.settings import REPO_ROOT

SCHEMA_PATH = REPO_ROOT / "shared" / "lesson.schema.json"


def render_schema() -> str:
    schema = Lesson.model_json_schema(mode="validation")
    schema = {"$schema": "https://json-schema.org/draft/2020-12/schema", **schema}
    return json.dumps(schema, indent=2, ensure_ascii=False) + "\n"


def write_schema() -> None:
    SCHEMA_PATH.write_text(render_schema(), encoding="utf-8", newline="\n")
