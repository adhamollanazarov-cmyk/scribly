"""Lesson JSON contract (docs/LESSON_SCHEMA.md). Source of truth for shared/lesson.schema.json."""

from typing import Annotated, Any, Literal, Self

from pydantic import BaseModel, ConfigDict, Field, ValidationInfo, model_validator

MAX_SAY_WORDS = 30
MAX_STEPS_WITHOUT_CHECKPOINT = 4
UNVERIFIED_NOTE = "I could not verify this number."

Color = Literal[
    "ink", "accent", "charge_pos", "charge_neg", "field", "surface", "force", "highlight", "wrong",
    "right",
]  # fmt: skip
Point = tuple[float, float]
Positive = Annotated[float, Field(gt=0)]


class Strict(BaseModel):
    """Unknown fields are errors, so AI typos fail validation instead of being dropped."""

    model_config = ConfigDict(extra="forbid", validate_by_name=False, serialize_by_alias=True)


class PrimitiveBase(Strict):
    model_config = ConfigDict(allow_inf_nan=False)

    id: str = Field(min_length=1, pattern=r"^[A-Za-z0-9_-]+$")
    color: Color | None = None
    at: float | None = Field(default=None, ge=0, le=1)
    label: str | None = None
    group: str | None = Field(
        default=None, description="Set by the server on template children. AI must not set it."
    )

    @model_validator(mode="after")
    def check_server_fields(self, info: ValidationInfo) -> Self:
        if info.context and info.context.get("raw_input") and "group" in self.model_fields_set:
            raise ValueError("group is set by the server only")
        return self


class PointPrim(PrimitiveBase):
    type: Literal["point"]
    x: float
    y: float
    r: Positive = 6


class LinePrim(PrimitiveBase):
    type: Literal["line"]
    x1: float
    y1: float
    x2: float
    y2: float
    dashed: bool = False


class ArrowPrim(PrimitiveBase):
    type: Literal["arrow"]
    x1: float
    y1: float
    x2: float
    y2: float
    dashed: bool = False


class VectorPrim(PrimitiveBase):
    type: Literal["vector"]
    from_: Point = Field(alias="from")
    to: Point
    name: str


class CirclePrim(PrimitiveBase):
    type: Literal["circle"]
    cx: float
    cy: float
    r: Positive
    dashed: bool = False


class EllipsePrim(PrimitiveBase):
    type: Literal["ellipse"]
    cx: float
    cy: float
    rx: Positive
    ry: Positive
    dashed: bool = False


class RectPrim(PrimitiveBase):
    type: Literal["rect"]
    x: float
    y: float
    w: Positive
    h: Positive
    dashed: bool = False


class PolylinePrim(PrimitiveBase):
    type: Literal["polyline"]
    points: list[Point] = Field(min_length=2)
    closed: bool = False


class CurvePrim(PrimitiveBase):
    type: Literal["curve"]
    points: list[Point] = Field(min_length=2)


class TextPrim(PrimitiveBase):
    type: Literal["text"]
    x: float
    y: float
    text: str = Field(min_length=1)
    size: Positive | None = None


class MathPrim(PrimitiveBase):
    type: Literal["math"]
    x: float
    y: float
    latex: str = Field(min_length=1)
    size: Positive | None = None


class SymbolPrim(PrimitiveBase):
    """A legend entry: introduces a symbol before any formula uses it (AGENTS.md §4)."""

    type: Literal["symbol"]
    x: float
    y: float
    symbol: str = Field(min_length=1, description=r"LaTeX, e.g. \Phi or Q_{\text{enc}}")
    meaning: str = Field(min_length=1)
    unit: str | None = Field(default=None, description="SI unit text; null if dimensionless")


class AxesPrim(PrimitiveBase):
    type: Literal["axes"]
    x: float
    y: float
    w: Positive
    h: Positive
    xlabel: str
    ylabel: str


class PlotPrim(PrimitiveBase):
    type: Literal["plot"]
    axes_id: str
    expr: str
    x_min: float
    x_max: float


class HighlightPrim(PrimitiveBase):
    type: Literal["highlight"]
    target_id: str


class MarkWrongPrim(PrimitiveBase):
    type: Literal["mark_wrong"]
    target_id: str
    reason: str = Field(min_length=1)


class ErasePrim(PrimitiveBase):
    type: Literal["erase"]
    target_id: str


class TemplatePrim(PrimitiveBase):
    type: Literal["template"]
    name: str
    params: dict[str, Any] = Field(default_factory=dict)


Primitive = Annotated[
    PointPrim | LinePrim | ArrowPrim | VectorPrim | CirclePrim | EllipsePrim | RectPrim
    | PolylinePrim | CurvePrim | TextPrim | MathPrim | SymbolPrim | AxesPrim | PlotPrim
    | HighlightPrim | MarkWrongPrim | ErasePrim | TemplatePrim,
    Field(discriminator="type"),
]  # fmt: skip

TargetPrim = HighlightPrim | MarkWrongPrim | ErasePrim


class Rect(Strict):
    model_config = ConfigDict(allow_inf_nan=False)

    x: float
    y: float
    w: Positive
    h: Positive


class Subtitles(Strict):
    uz: str | None = None
    ru: str | None = None


class Checkpoint(Strict):
    question: str = Field(min_length=1)
    type: Literal["choice", "number"]
    choices: list[str] | None = None
    answer: int | float
    tolerance: float | None = Field(default=None, ge=0)
    unit: str | None = None
    hint: str | None = None
    reexplain_hint: str | None = None

    @model_validator(mode="after")
    def check_shape(self) -> Self:
        if self.type == "choice":
            if not self.choices or len(self.choices) < 2:
                raise ValueError("choice checkpoint needs at least 2 choices")
            if not isinstance(self.answer, int) or not 0 <= self.answer < len(self.choices):
                raise ValueError("choice answer must be the index of one of the choices")
        elif not self.unit:
            raise ValueError("number checkpoint needs a unit")
        return self


class Slider(Strict):
    id: str = Field(min_length=1)
    label: str
    min: float
    max: float
    value: float
    binds: list[str] = Field(min_length=1)

    @model_validator(mode="after")
    def check_range(self) -> Self:
        if not self.min <= self.value <= self.max:
            raise ValueError("slider needs min <= value <= max")
        for bind in self.binds:
            if bind.count(".") != 1:
                raise ValueError(f"slider bind {bind!r} must look like '<primitive id>.<field>'")
        return self


class Step(Strict):
    id: str = Field(min_length=1)
    kind: Literal["explain", "checkpoint", "summary", "branch"]
    say: str = Field(min_length=1)
    subtitles: Subtitles = Field(default_factory=Subtitles)
    draw: list[Primitive] = Field(default_factory=list)
    focus: Rect | None = None
    checkpoint: Checkpoint | None = None
    sliders: list[Slider] = Field(default_factory=list)
    warning: Literal["unverified"] | None = Field(
        default=None, description="Set by the server after verification. AI must not set it."
    )

    @model_validator(mode="after")
    def check_step(self, info: ValidationInfo) -> Self:
        if info.context and info.context.get("raw_input") and "warning" in self.model_fields_set:
            raise ValueError("warning is set by the server only")
        narration = self.say
        if self.warning == "unverified":
            narration = narration.removesuffix(f" {UNVERIFIED_NOTE}")
        words = len(narration.split())
        if words > MAX_SAY_WORDS:
            raise ValueError(f"say has {words} words; the limit is {MAX_SAY_WORDS}")
        if (self.kind == "checkpoint") != (self.checkpoint is not None):
            raise ValueError("a checkpoint step needs a checkpoint, and only checkpoint steps")
        return self


class Source(Strict):
    type: Literal["topic", "problem", "screenshot"]
    text: str


class Calc(Strict):
    id: str = Field(min_length=1)
    expr: str = Field(min_length=1)
    values: dict[str, float] = Field(default_factory=dict)
    expected: float
    unit: str = Field(min_length=1)
    rel_tol: float = Field(default=0.01, gt=0)
    used_in_steps: list[str] = Field(default_factory=list)


class Lesson(Strict):
    version: Literal["1"] = "1"
    id: str = Field(min_length=1)
    title: str = Field(min_length=1)
    level: Literal["simple", "university", "exam"]
    source: Source
    steps: list[Step] = Field(min_length=1)
    calcs: list[Calc] = Field(default_factory=list)

    @model_validator(mode="after")
    def check_lesson(self) -> Self:
        step_ids = [step.id for step in self.steps]
        _require_unique(step_ids, "step id")
        _require_unique([p.id for step in self.steps for p in step.draw], "primitive id")
        for calc in self.calcs:
            unknown = set(calc.used_in_steps) - set(step_ids)
            if unknown:
                raise ValueError(f"calc {calc.id} uses unknown steps: {sorted(unknown)}")
        _check_checkpoint_spacing(self.steps)
        return self


class StreamedStep(Step):
    """A `step` SSE event: the step plus its narration audio (null if TTS failed)."""

    audio_url: str | None


def _require_unique(ids: list[str], what: str) -> None:
    seen: set[str] = set()
    for item in ids:
        if item in seen:
            raise ValueError(f"duplicate {what}: {item}")
        seen.add(item)


def _check_checkpoint_spacing(steps: list[Step]) -> None:
    run = 0
    for index, step in enumerate(steps):
        run = 0 if step.kind == "checkpoint" else run + 1
        final_summary = index == len(steps) - 1 and step.kind == "summary"
        if run > MAX_STEPS_WITHOUT_CHECKPOINT and not final_summary:
            raise ValueError(
                f"step {step.id}: more than {MAX_STEPS_WITHOUT_CHECKPOINT} steps without a "
                "checkpoint"
            )


def check_references(lesson: Lesson) -> list[str]:
    """Problems with target ids and slider binds. Run after template expansion."""
    errors: list[str] = []
    drawn: dict[str, PrimitiveBase] = {}
    groups: set[str] = set()
    for step in lesson.steps:
        errors += check_step_references(step, drawn, groups)
    return errors


def check_step_references(
    step: Step, drawn: dict[str, PrimitiveBase], groups: set[str]
) -> list[str]:
    """Reference problems in one step; records its primitives in `drawn` and `groups`."""
    errors: list[str] = []
    for prim in step.draw:
        if isinstance(prim, TargetPrim) and not prim_id_known(prim, drawn, groups):
            errors.append(f"step {step.id}: {prim.id} targets unknown {prim.target_id!r}")
        drawn[prim.id] = prim
        if prim.group:
            groups.add(prim.group)
    for slider in step.sliders:
        for bind in slider.binds:
            prim_id, field = bind.split(".")
            target = drawn.get(prim_id)
            if target is None or field not in type(target).model_fields:
                errors.append(f"step {step.id}: slider {slider.id} binds unknown {bind!r}")
    return errors


def prim_id_known(prim: TargetPrim, drawn: dict[str, PrimitiveBase], groups: set[str]) -> bool:
    return prim.target_id in drawn or prim.target_id in groups
