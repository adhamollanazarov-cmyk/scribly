"""The draft format the model writes, and its structured-output JSON schema.

The API compiles the output schema into a grammar with a small budget (measured
2026-10-10: a flat object of ~70 required properties is already "too large"), so the
full typed lesson cannot be enforced by the grammar. The grammar enforces the lesson
skeleton (steps, calcs, checkpoints, subtitles) and one generic draw item whose
arguments are typed key/value lists; Pydantic then checks each item against the
contract (models.py, templates.py) and reports problems per step.

Every field is required and non-nullable ("" and [] replace null). Field order is
generation order: calcs come before `say` inside each step, so a step can be verified
and streamed as soon as it is complete.
"""

from typing import Any, Literal, Self

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.lesson.direction import normalize
from app.lesson.models import Color
from app.lesson.templates import TEMPLATES

PLAIN_TYPES = (
    "point",
    "line",
    "arrow",
    "vector",
    "circle",
    "ellipse",
    "rect",
    "polyline",
    "curve",
    "text",
    "math",
    "symbol",
    "axes",
    "plot",
    "highlight",
    "mark_wrong",
    "erase",
)
DRAW_TYPES = (*PLAIN_TYPES, *TEMPLATES)
DrawType = Literal[DRAW_TYPES]  # type: ignore[valid-type]


class Draft(BaseModel):
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)


class ValueDraft(Draft):
    name: str = Field(description="Variable name used in expr, e.g. q or lam")
    value: float = Field(description="SI value, e.g. 3e-9 for 3 nC")


class CalcDraft(Draft):
    id: str = Field(description="c1, c2, ... unique in the lesson")
    expr: str = Field(description="Arithmetic in the value names; allowed functions only")
    values: list[ValueDraft]
    quantity_kind: Literal["scalar", "magnitude", "component", "oriented"]
    frame: str = Field(
        description='Reference ID shared with convention drawings; "" for scalars/magnitudes'
    )
    positive: str = Field(
        description='What a positive result means, e.g. +x, A->B, down the slope; "" if '
        "the result has no direction",
    )
    expected: float = Field(description="Your own full-precision signed result of expr")
    unit: str = Field(description="SymPy-style unit of the result, e.g. N*m**2/C; 1 if none")
    unit_spoken: str = Field(description="Unit as spoken, e.g. newton meters squared per coulomb")

    @model_validator(mode="after")
    def check_direction(self) -> Self:
        if self.quantity_kind in ("component", "oriented"):
            if not normalize(self.positive):
                raise ValueError(
                    "components/oriented quantities need readable positive, including zero"
                )
            if not self.frame.strip() or self.frame != self.frame.strip():
                raise ValueError("components/oriented quantities need a nonempty, trimmed frame ID")
        elif self.positive != "" or self.frame != "":
            raise ValueError("scalars/magnitudes need empty positive and frame")
        if self.quantity_kind == "magnitude" and self.expected < 0:
            raise ValueError("a magnitude cannot be negative")
        return self


class NumArg(Draft):
    k: str
    v: float


class TextArg(Draft):
    k: str
    v: str


class DrawDraft(Draft):
    id: str = Field(description="Unique in the lesson: letters, digits, _ and -")
    type: DrawType
    color: Color
    label: str = Field(description='Short label, or "" for none')
    frame: str = Field(default="", description='Reference ID for convention drawings; otherwise ""')
    at: float = Field(description="0-1: when in the narration it starts")
    num: list[NumArg] = Field(description="Numeric arguments by name; booleans as 1 or 0")
    txt: list[TextArg] = Field(description="Text arguments by name")
    pts: list[list[float]] = Field(description="[[x, y], ...] for polyline/curve; else []")


class Subtitles(Draft):
    uz: str
    ru: str


class CheckpointDraft(Draft):
    question: str
    type: Literal["choice", "number"]
    choices: list[str] = Field(description="2-4 options for choice; [] for number")
    answer: str = Field(
        description='choice: index of the right option as digits, e.g. "1"; '
        'number: a calc placeholder, e.g. "{c3:3sf}"'
    )
    hint: str
    reexplain_hint: str = Field(description="A different approach for a wrong answer")

    @model_validator(mode="after")
    def check_shape(self) -> Self:
        if self.type == "choice":
            if not 2 <= len(self.choices) <= 6:
                raise ValueError("a choice checkpoint needs 2 to 6 choices")
            if not self.answer.isdigit() or int(self.answer) >= len(self.choices):
                raise ValueError("a choice answer must be the index of one of the choices")
        elif self.choices:
            raise ValueError("a number checkpoint has no choices")
        return self


class StepDraft(Draft):
    id: str = Field(description="s1, s2, ...")
    kind: Literal["explain", "checkpoint", "summary"]
    calcs: list[CalcDraft] = Field(description="Calcs this step introduces, [] if none")
    say: str = Field(description="Spoken narration, one idea, at most 26 words")
    subtitles: Subtitles
    draw: list[DrawDraft]
    checkpoints: list[CheckpointDraft] = Field(description="Exactly one if kind is checkpoint")

    @model_validator(mode="after")
    def check_checkpoint(self) -> Self:
        if len(self.checkpoints) > 1:
            raise ValueError("a step has at most one checkpoint")
        if (self.kind == "checkpoint") != bool(self.checkpoints):
            raise ValueError("a checkpoint step needs one checkpoint, and only checkpoint steps")
        return self


class LessonHeader(Draft):
    title: str
    level: Literal["simple", "university", "exam"]


class LessonDraft(LessonHeader):
    steps: list[StepDraft]


class StepFix(Draft):
    steps: list[StepDraft] = Field(
        description="The corrected step; or a new checkpoint step followed by the corrected step"
    )


# --- draft item -> contract primitive ---------------------------------------------------

VECTOR_ENDS = ("x1", "y1", "x2", "y2")
BOOL_ARGS = {"dashed", "closed"}
FORCE_ARGS = ("name", "angle_deg", "length")


def contract_primitive(item: DrawDraft) -> dict[str, Any]:
    """The contract JSON for a draft item. Unknown or missing args surface later as
    Pydantic errors from the contract models, which name the field."""
    head: dict[str, Any] = {"id": item.id, "color": item.color, "at": item.at}
    if item.label:
        head["label"] = item.label
    nums = {a.k: a.v for a in item.num}
    txts = {a.k: a.v for a in item.txt}
    if item.type in TEMPLATES:
        return {**head, "type": "template", "name": item.type, "params": _template_params(item)}
    args: dict[str, Any] = {**nums, **txts}
    reserved = args.keys() & {"id", "type", "color", "at", "label", "group"}
    if reserved:
        raise ValueError(
            f"{item.id}: arguments cannot override metadata: {', '.join(sorted(reserved))}"
        )
    for key in BOOL_ARGS & args.keys():
        args[key] = bool(args[key])
    if item.type == "vector" and all(k in nums for k in VECTOR_ENDS):
        for key in VECTOR_ENDS:
            del args[key]
        args["from"] = [nums["x1"], nums["y1"]]
        args["to"] = [nums["x2"], nums["y2"]]
    if item.type in ("polyline", "curve"):
        args["points"] = item.pts
    if item.type == "symbol" and args.get("unit") == "":
        del args["unit"]
    return {**head, "type": item.type, **args}


def _template_params(item: DrawDraft) -> dict[str, Any]:
    params: dict[str, Any] = {}
    forces: dict[str, list[Any]] = {k: [] for k in FORCE_ARGS}
    args: list[NumArg | TextArg] = [*item.num, *item.txt]
    for arg in args:
        if item.type == "free_body" and arg.k in forces:
            forces[arg.k].append(arg.v)
        elif isinstance(arg, NumArg) and float(arg.v).is_integer() and _int_param(item, arg.k):
            params[arg.k] = int(arg.v)
        elif isinstance(arg, TextArg) and arg.v == "":
            continue  # "" means "not set": keep the template default
        else:
            params[arg.k] = arg.v
    if item.type == "free_body":
        if len({len(v) for v in forces.values()}) != 1:
            raise ValueError(f"{item.id}: free_body needs one name, angle_deg and length per force")
        params["forces"] = [
            dict(zip(FORCE_ARGS, f, strict=True)) for f in zip(*forces.values(), strict=True)
        ]
    return params


def _int_param(item: DrawDraft, key: str) -> bool:
    field = TEMPLATES[item.type][0].model_fields.get(key)
    return field is not None and field.annotation is int


# --- structured-output schema ---------------------------------------------------------

DROPPED_KEYS = {"title", "default", "discriminator"}
MOVED_KEYS = {
    "minimum",
    "maximum",
    "exclusiveMinimum",
    "exclusiveMaximum",
    "multipleOf",
    "minLength",
    "maxLength",
    "maxItems",
    "uniqueItems",
    "prefixItems",
    "pattern",
}


def generation_schema(model: type[Draft]) -> dict[str, Any]:
    """JSON schema for `output_config.format`, inside the structured-output limits.

    `$ref`s are inlined: the API's grammar budget is noticeably smaller with them.
    """
    schema = model.model_json_schema()
    defs = schema.pop("$defs", {})
    strict: dict[str, Any] = _strict(_inline(schema, defs))
    return strict


def _inline(node: Any, defs: dict[str, Any]) -> Any:
    if isinstance(node, list):
        return [_inline(item, defs) for item in node]
    if not isinstance(node, dict):
        return node
    if "$ref" in node:
        return _inline(defs[node["$ref"].rsplit("/", 1)[1]], defs)
    return {key: _inline(value, defs) for key, value in node.items()}


def _strict(node: Any) -> Any:
    if isinstance(node, list):
        return [_strict(item) for item in node]
    if not isinstance(node, dict):
        return node
    out: dict[str, Any] = {}
    moved: list[str] = []
    for key, value in node.items():
        if key in DROPPED_KEYS:
            continue
        if key in MOVED_KEYS or (key == "minItems" and value not in (0, 1)):
            moved.append(f"{key} {value}")
        elif key == "const":
            out["enum"] = [value]
        elif key == "oneOf":
            out["anyOf"] = _strict(value)
        elif key == "properties":
            out[key] = {name: _strict(sub) for name, sub in value.items()}
        else:
            out[key] = _strict(value)
    if moved:
        out["description"] = "; ".join(filter(None, [out.get("description"), *moved]))
    if out.get("type") == "object" and "properties" in out:
        out["additionalProperties"] = False
        out["required"] = list(out["properties"])
    return out
