import json

from app.lesson.schema_export import SCHEMA_PATH, render_schema


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
