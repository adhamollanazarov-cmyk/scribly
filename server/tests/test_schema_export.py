import json
import re

from app.lesson.schema_export import SCHEMA_PATH, render_schema
from app.lesson.templates import TEMPLATES


def test_shared_schema_is_up_to_date() -> None:
    on_disk = SCHEMA_PATH.read_text(encoding="utf-8").replace("\r\n", "\n")

    assert on_disk == render_schema(), (
        "shared/lesson.schema.json is stale. Run in server/: uv run python -m scripts.gen_schema"
    )


def test_schema_describes_every_primitive_type() -> None:
    schema = json.loads(render_schema())
    mapping = schema["$defs"]["Step"]["properties"]["draw"]["items"]["discriminator"]["mapping"]

    assert sorted(mapping) == sorted(
        ["point", "line", "arrow", "vector", "circle", "ellipse", "rect", "polyline", "curve",
         "text", "math", "axes", "plot", "highlight", "mark_wrong", "erase", "template"]
    )  # fmt: skip


def test_schema_document_lists_actual_primitive_types_and_templates() -> None:
    doc = (SCHEMA_PATH.parent.parent / "docs/LESSON_SCHEMA.md").read_text(encoding="utf-8")
    schema = json.loads(render_schema())
    mapping = schema["$defs"]["Step"]["properties"]["draw"]["items"]["discriminator"]["mapping"]
    primitive_section = doc.split("## Primitive", 1)[1].split("## Templates", 1)[0]
    template_section = doc.split("## Templates", 1)[1].split("## Checkpoint", 1)[0]

    assert set(re.findall(r"^\| `([a-z_]+)` \|", primitive_section, re.M)) == set(mapping)
    assert set(re.findall(r"^\| `([a-z_]+)` \|", template_section, re.M)) == set(TEMPLATES)
