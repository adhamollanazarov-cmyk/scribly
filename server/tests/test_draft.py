import json
from typing import Any

import pytest

from app.lesson.draft import (
    DRAW_TYPES,
    DrawDraft,
    LessonDraft,
    StepDraft,
    StepFix,
    contract_primitive,
    generation_schema,
)
from app.lesson.models import Step
from app.lesson.templates import TEMPLATES, expand_step
from tests.drafts import choice, item, step

UNSUPPORTED = {
    "minimum",
    "maximum",
    "exclusiveMinimum",
    "exclusiveMaximum",
    "minLength",
    "maxLength",
    "maxItems",
    "uniqueItems",
    "prefixItems",
    "multipleOf",
    "$ref",
    "$defs",
    "oneOf",
    "discriminator",
    "const",
    "pattern",
}
# Measured 2026-10-10: ~70 required properties already make the grammar "too large".
PROPERTY_BUDGET = 45


def walk(node: Any) -> list[dict[str, Any]]:
    if isinstance(node, dict):
        return [node, *(n for v in node.values() for n in walk(v))]
    if isinstance(node, list):
        return [n for v in node for n in walk(v)]
    return []


@pytest.mark.parametrize("model", [LessonDraft, StepFix])
def test_schema_fits_structured_output_limits(model: type[LessonDraft] | type[StepFix]) -> None:
    nodes = walk(generation_schema(model))

    objects = [n for n in nodes if n.get("type") == "object"]
    assert all(n["additionalProperties"] is False for n in objects)
    assert all(set(n["required"]) == set(n["properties"]) for n in objects)  # no optional
    assert not [n for n in nodes if "anyOf" in n or isinstance(n.get("type"), list)]  # no unions
    assert not {k for n in nodes for k in n} & UNSUPPORTED
    assert all(n.get("minItems", 0) in (0, 1) for n in nodes)
    assert sum(len(n["properties"]) for n in objects) <= PROPERTY_BUDGET


def test_step_fields_are_in_generation_order() -> None:
    props = generation_schema(LessonDraft)["properties"]
    assert list(props) == ["title", "level", "steps"]
    step_props = props["steps"]["items"]["properties"]
    assert list(step_props)[:4] == ["id", "kind", "calcs", "say"]


def test_draw_type_enum_lists_plain_types_and_templates() -> None:
    schema = generation_schema(LessonDraft)
    enum = schema["properties"]["steps"]["items"]["properties"]["draw"]["items"]["properties"][
        "type"
    ]["enum"]
    assert set(enum) == set(DRAW_TYPES) and set(TEMPLATES) <= set(enum)


def to_contract(raw: dict[str, Any]) -> dict[str, Any]:
    return contract_primitive(DrawDraft.model_validate(raw))


def test_plain_items_become_contract_primitives() -> None:
    assert to_contract(item("a", "line", {"x1": 0, "y1": 0, "x2": 5, "y2": 5, "dashed": 1})) == {
        "id": "a",
        "color": "ink",
        "at": 0.5,
        "type": "line",
        "x1": 0,
        "y1": 0,
        "x2": 5,
        "y2": 5,
        "dashed": True,
    }
    vec = to_contract(item("v", "vector", {"x1": 1, "y1": 2, "x2": 3, "y2": 4}, {"name": "F"}))
    assert vec["from"] == [1, 2] and vec["to"] == [3, 4] and "x1" not in vec
    poly = to_contract(item("p", "polyline", {"closed": 0}, pts=[[0, 0], [1, 1]], label="road"))
    assert poly["points"] == [[0, 0], [1, 1]] and poly["closed"] is False
    assert poly["label"] == "road"
    sym = to_contract(
        item("s", "symbol", {"x": 1, "y": 2}, {"symbol": "k", "meaning": "ratio", "unit": ""})
    )
    assert "unit" not in sym


def test_template_items_keep_defaults_and_group_forces() -> None:
    charge = to_contract(item("q", "point_charge", {"x": 1, "y": 2}, {"sign": "-", "name": ""}))
    assert charge == {
        "id": "q",
        "color": "ink",
        "at": 0.5,
        "type": "template",
        "name": "point_charge",
        "params": {"x": 1, "y": 2, "sign": "-"},
    }
    lines = to_contract(item("f", "radial_field_lines", {"x": 1, "y": 2, "n": 8.0}))
    assert lines["params"]["n"] == 8 and isinstance(lines["params"]["n"], int)
    body = DrawDraft.model_validate(
        {
            **item("b", "free_body", {"x": 100, "y": 100}),
            "num": [
                {"k": "x", "v": 100},
                {"k": "y", "v": 100},
                {"k": "angle_deg", "v": 270},
                {"k": "length", "v": 80},
                {"k": "angle_deg", "v": 90},
                {"k": "length", "v": 60},
            ],
            "txt": [{"k": "name", "v": "W"}, {"k": "name", "v": "N"}],
        }
    )
    forces = contract_primitive(body)["params"]["forces"]
    assert forces == [
        {"name": "W", "angle_deg": 270, "length": 80},
        {"name": "N", "angle_deg": 90, "length": 60},
    ]


def test_free_body_with_unmatched_force_args_is_an_error() -> None:
    body = item("b", "free_body", {"x": 1, "y": 1, "angle_deg": 90}, {"name": "W"})
    with pytest.raises(ValueError, match="one name, angle_deg and length per force"):
        to_contract(body)


def test_converted_template_expands_with_the_real_template_code() -> None:
    raw = to_contract(item("q", "point_charge", {"x": 300, "y": 400}, {"sign": "+"}))
    expanded = expand_step(Step(id="s1", kind="explain", say="x", draw=[raw]))  # type: ignore[list-item]
    assert {p.id for p in expanded.draw} == {"q-charge", "q-sign-h", "q-sign-v"}


@pytest.mark.parametrize(
    ("raw", "message"),
    [
        (step("s1", "x", kind="checkpoint"), "checkpoint step needs one checkpoint"),
        ({**step("s1", "x"), "checkpoints": [choice()]}, "only checkpoint steps"),
        (step("s1", "x", kind="checkpoint", checkpoint=choice(answer="7")), "index of one"),
        (
            step("s1", "x", kind="checkpoint", checkpoint={**choice(), "type": "number"}),
            "number checkpoint has no choices",
        ),
        ({**step("s1", "x"), "draw": [item("a", "hexagon")]}, "Input should be"),
    ],
)
def test_bad_step_drafts_are_rejected_with_a_reason(raw: dict[str, Any], message: str) -> None:
    with pytest.raises(ValueError, match=message):
        StepDraft.model_validate(raw)


def test_draft_round_trips_through_json() -> None:
    raw = step("s1", "Hello.", [item("t", "text", {"x": 1, "y": 2}, {"text": "hi"})])
    assert StepDraft.model_validate(json.loads(json.dumps(raw))).model_dump() == raw
