"""The lesson system prompt: prompt.md plus a template catalogue generated from the
template parameter models, so the prompt cannot drift from templates.py."""

import types
from functools import lru_cache
from pathlib import Path
from typing import Any, Literal, Union, get_args, get_origin

from pydantic.fields import FieldInfo

from app.lesson.templates import TEMPLATES, Params

PROMPT_PATH = Path(__file__).with_name("prompt.md")

CHILDREN = {
    "point_charge": "-charge circle, -sign-h line, -sign-v line (only for +)",
    "radial_field_lines": "-1 ... -n arrows",
    "gaussian_sphere": "-sphere dashed circle",
    "charged_plane": "-plane line, -q1 ... -qn points, -e1 ... -e2n field arrows on both sides",
    "incline_block": "-incline polyline, -block polyline, -angle text. (x, y) is the right-angle "
    "corner at the bottom left; the slope rises from bottom-right to top-left",
    "free_body": "-body rect, -f1 ... -fn vectors from the body centre. For each force add one "
    "txt name, one num angle_deg and one num length, in the same order",
    "axes_plot": "-axes axes, -curve curve. (x, y) is the top-left of the plot box; expr is in "
    "x with the calc grammar; the server samples it",
}


@lru_cache
def system_prompt() -> str:
    text = PROMPT_PATH.read_text(encoding="utf-8")
    return text.replace("{template_catalogue}", template_catalogue())


def template_catalogue() -> str:
    lines = ["| template | num | txt | children |", "|---|---|---|---|"]
    for name, (params, _) in TEMPLATES.items():
        nums, txts = _arguments(params)
        lines.append(f"| {name} | {', '.join(nums)} | {', '.join(txts)} | {CHILDREN[name]} |")
    return "\n".join(lines)


def _arguments(params: type[Params]) -> tuple[list[str], list[str]]:
    nums: list[str] = []
    txts: list[str] = []
    for field_name, info in params.model_fields.items():
        kind, choices = _kind(info.annotation)
        if kind == "list":
            continue  # free_body forces: described in CHILDREN
        text = field_name + _default(info) + (f" ({' / '.join(choices)})" if choices else "")
        (txts if kind == "text" else nums).append(text)
    return nums, txts


def _kind(annotation: Any) -> tuple[str, list[str]]:
    origin = get_origin(annotation)
    if origin is Literal:
        return "text", [str(a) for a in get_args(annotation)]
    if origin in (Union, types.UnionType):
        inner = [a for a in get_args(annotation) if a is not type(None)]
        return _kind(inner[0])
    if origin is list:
        return "list", []
    return ("text" if annotation is str else "num"), []


def _default(info: FieldInfo) -> str:
    if info.is_required():
        return ""
    if info.default is None:
        return " (optional)"
    return f" (default {info.default})"
