"""Expand `template` primitives into plain primitives. Pure and deterministic.

Conventions: canvas px, y points down; angles in degrees, counter-clockwise from +x as
seen on screen. Children are named `<template id>-<part>` and carry `group=<template id>`.
"""

import math
from collections.abc import Callable
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, ValidationError

from app.lesson.models import (
    ArrowPrim,
    AxesPrim,
    CirclePrim,
    CurvePrim,
    Lesson,
    LinePrim,
    Point,
    PointPrim,
    PolylinePrim,
    RectPrim,
    Step,
    TemplatePrim,
    TextPrim,
    VectorPrim,
)
from app.lesson.safe_expr import ExpressionError, evaluate, parse

Child = BaseModel  # any concrete primitive model


class TemplateError(ValueError):
    """Unknown template name, bad params, or params that cannot be drawn."""


class Params(BaseModel):
    model_config = ConfigDict(extra="forbid")


def r1(value: float) -> float:
    return round(value, 1)


def polar(x: float, y: float, radius: float, angle_deg: float) -> Point:
    angle = math.radians(angle_deg)
    return r1(x + radius * math.cos(angle)), r1(y - radius * math.sin(angle))


# --- point_charge ---------------------------------------------------------------------


class PointChargeParams(Params):
    x: float
    y: float
    sign: Literal["+", "-"] = "+"
    r: float = Field(default=16, gt=0)
    name: str | None = None


def point_charge(tid: str, p: PointChargeParams) -> list[Child]:
    color = "charge_pos" if p.sign == "+" else "charge_neg"
    arm = r1(p.r * 0.55)
    children: list[Child] = [
        CirclePrim(id=f"{tid}-charge", type="circle", cx=p.x, cy=p.y, r=p.r, color=color,
                   label=p.name),
        LinePrim(id=f"{tid}-sign-h", type="line", x1=r1(p.x - arm), y1=p.y, x2=r1(p.x + arm),
                 y2=p.y, color=color),
    ]  # fmt: skip
    if p.sign == "+":
        children.append(
            LinePrim(id=f"{tid}-sign-v", type="line", x1=p.x, y1=r1(p.y - arm), x2=p.x,
                     y2=r1(p.y + arm), color=color)
        )  # fmt: skip
    return children


# --- radial_field_lines -------------------------------------------------------------------


class RadialFieldLinesParams(Params):
    x: float
    y: float
    n: int = Field(default=8, ge=1, le=36)
    r_start: float = Field(default=30, ge=0)
    r_end: float = Field(default=200, gt=0)
    direction: Literal["out", "in"] = "out"
    angle_offset: float = 0


def radial_field_lines(tid: str, p: RadialFieldLinesParams) -> list[Child]:
    if p.r_end <= p.r_start:
        raise TemplateError("radial_field_lines needs r_end > r_start")
    arrows: list[Child] = []
    for i in range(p.n):
        angle = p.angle_offset + 360 * i / p.n
        (x1, y1), (x2, y2) = polar(p.x, p.y, p.r_start, angle), polar(p.x, p.y, p.r_end, angle)
        if p.direction == "in":
            (x1, y1), (x2, y2) = (x2, y2), (x1, y1)
        arrows.append(
            ArrowPrim(id=f"{tid}-{i + 1}", type="arrow", x1=x1, y1=y1, x2=x2, y2=y2,
                      color="field")
        )  # fmt: skip
    return arrows


# --- gaussian_sphere -------------------------------------------------------------------


class GaussianSphereParams(Params):
    cx: float
    cy: float
    r: float = Field(gt=0)
    name: str | None = None


def gaussian_sphere(tid: str, p: GaussianSphereParams) -> list[Child]:
    return [
        CirclePrim(id=f"{tid}-sphere", type="circle", cx=p.cx, cy=p.cy, r=p.r, dashed=True,
                   color="surface", label=p.name)
    ]  # fmt: skip


# --- charged_plane ---------------------------------------------------------------------


class ChargedPlaneParams(Params):
    x: float
    y: float
    length: float = Field(default=600, gt=0)
    orientation: Literal["vertical", "horizontal"] = "vertical"
    sign: Literal["+", "-"] = "+"
    n: int = Field(default=5, ge=1, le=20)
    field_length: float = Field(default=120, gt=0)


def charged_plane(tid: str, p: ChargedPlaneParams) -> list[Child]:
    # Work in (along, across) coordinates, then map to the canvas.
    def at(along: float, across: float) -> Point:
        if p.orientation == "vertical":
            return r1(p.x + across), r1(p.y + along)
        return r1(p.x + along), r1(p.y + across)

    half = p.length / 2
    (x1, y1), (x2, y2) = at(-half, 0), at(half, 0)
    children: list[Child] = [LinePrim(id=f"{tid}-plane", type="line", x1=x1, y1=y1, x2=x2,
                                      y2=y2, color="ink")]  # fmt: skip
    color = "charge_pos" if p.sign == "+" else "charge_neg"
    gap, outward = 14.0, 1 if p.sign == "+" else -1
    for i in range(p.n):
        along = -half + p.length * (i + 0.5) / p.n
        cx, cy = at(along, 0)
        children.append(PointPrim(id=f"{tid}-q{i + 1}", type="point", x=cx, y=cy, r=5,
                                  color=color))  # fmt: skip
        for side, k in ((1, 2 * i + 1), (-1, 2 * i + 2)):
            near, far = at(along, side * gap), at(along, side * (gap + p.field_length))
            start, end = (near, far) if outward > 0 else (far, near)
            children.append(ArrowPrim(id=f"{tid}-e{k}", type="arrow", x1=start[0], y1=start[1],
                                      x2=end[0], y2=end[1], color="field"))  # fmt: skip
    return children


# --- incline_block ---------------------------------------------------------------------


class InclineBlockParams(Params):
    x: float
    y: float
    base: float = Field(default=500, gt=0)
    angle_deg: float = Field(default=30, gt=0, lt=80)
    block: float = Field(default=80, gt=0)


def incline_block(tid: str, p: InclineBlockParams) -> list[Child]:
    """Right angle at (x, y), bottom-left; slope rises from bottom-right to top-left."""
    theta = math.radians(p.angle_deg)
    height = p.base * math.tan(theta)
    a, b, c = (p.x, p.y), (p.x + p.base, p.y), (p.x, p.y - height)
    slope_len = math.hypot(p.base, height)
    if p.block >= slope_len:
        raise TemplateError("incline_block: block is longer than the slope")
    ux, uy = -math.cos(theta), -math.sin(theta)  # along the slope, up-left
    nx, ny = math.sin(theta), -math.cos(theta)  # out of the slope, up-right
    mx, my = (b[0] + c[0]) / 2, (b[1] + c[1]) / 2
    half = p.block / 2
    p1 = (mx - ux * half, my - uy * half)
    p2 = (mx + ux * half, my + uy * half)
    p3 = (p2[0] + nx * p.block, p2[1] + ny * p.block)
    p4 = (p1[0] + nx * p.block, p1[1] + ny * p.block)
    return [
        PolylinePrim(id=f"{tid}-incline", type="polyline", points=_round_points([a, b, c]),
                     closed=True, color="ink"),
        PolylinePrim(id=f"{tid}-block", type="polyline", points=_round_points([p1, p2, p3, p4]),
                     closed=True, color="accent"),
        TextPrim(id=f"{tid}-angle", type="text", x=r1(b[0] - 70), y=r1(b[1] - 10),
                 text=f"{p.angle_deg:g}°"),
    ]  # fmt: skip


# --- free_body -------------------------------------------------------------------------


class Force(Params):
    name: str = Field(min_length=1)
    angle_deg: float
    length: float = Field(gt=0)


class FreeBodyParams(Params):
    x: float
    y: float
    size: float = Field(default=40, gt=0)
    forces: list[Force] = Field(min_length=1, max_length=8)


def free_body(tid: str, p: FreeBodyParams) -> list[Child]:
    half = p.size / 2
    children: list[Child] = [
        RectPrim(id=f"{tid}-body", type="rect", x=r1(p.x - half), y=r1(p.y - half), w=p.size,
                 h=p.size, color="ink")
    ]  # fmt: skip
    for i, force in enumerate(p.forces, start=1):
        tip = polar(p.x, p.y, force.length, force.angle_deg)
        children.append(VectorPrim(id=f"{tid}-f{i}", type="vector", **{"from": (p.x, p.y)},
                                   to=tip, name=force.name, color="force"))  # fmt: skip
    return children


# --- axes_plot -------------------------------------------------------------------------


class AxesPlotParams(Params):
    x: float
    y: float
    w: float = Field(gt=0)
    h: float = Field(gt=0)
    xlabel: str = "x"
    ylabel: str = "y"
    expr: str
    x_min: float
    x_max: float
    y_min: float | None = None
    y_max: float | None = None
    samples: int = Field(default=41, ge=2, le=200)


def axes_plot(tid: str, p: AxesPlotParams) -> list[Child]:
    """(x, y) is the top-left of the plot box; the origin of the data maps to its corners."""
    if p.x_max <= p.x_min:
        raise TemplateError("axes_plot needs x_max > x_min")
    try:
        expr = parse(p.expr, ["x"])
        xs = [p.x_min + (p.x_max - p.x_min) * i / (p.samples - 1) for i in range(p.samples)]
        ys = [evaluate(expr, {"x": xv}) for xv in xs]
    except ExpressionError as e:
        raise TemplateError(f"axes_plot: {e}") from e
    y_min = min(ys) if p.y_min is None else p.y_min
    y_max = max(ys) if p.y_max is None else p.y_max
    if y_max <= y_min:
        y_min, y_max = y_min - 1, y_max + 1
    points = [
        (
            p.x + (xv - p.x_min) / (p.x_max - p.x_min) * p.w,
            p.y + p.h - (min(max(yv, y_min), y_max) - y_min) / (y_max - y_min) * p.h,
        )
        for xv, yv in zip(xs, ys, strict=True)
    ]
    return [
        AxesPrim(id=f"{tid}-axes", type="axes", x=p.x, y=p.y, w=p.w, h=p.h, xlabel=p.xlabel,
                 ylabel=p.ylabel, color="ink"),
        CurvePrim(id=f"{tid}-curve", type="curve", points=_round_points(points), color="accent"),
    ]  # fmt: skip


# --- registry and expansion ------------------------------------------------------------

Template = tuple[type[Params], Callable[[str, Any], list[Child]]]
TEMPLATES: dict[str, Template] = {
    "point_charge": (PointChargeParams, point_charge),
    "radial_field_lines": (RadialFieldLinesParams, radial_field_lines),
    "gaussian_sphere": (GaussianSphereParams, gaussian_sphere),
    "charged_plane": (ChargedPlaneParams, charged_plane),
    "incline_block": (InclineBlockParams, incline_block),
    "free_body": (FreeBodyParams, free_body),
    "axes_plot": (AxesPlotParams, axes_plot),
}


def expand_template(prim: TemplatePrim) -> list[Child]:
    if prim.name not in TEMPLATES:
        raise TemplateError(f"unknown template {prim.name!r}; known: {sorted(TEMPLATES)}")
    params_model, build = TEMPLATES[prim.name]
    try:
        params = params_model.model_validate(prim.params)
    except ValidationError as e:
        raise TemplateError(f"template {prim.id} ({prim.name}): bad params: {e}") from e
    children = build(prim.id, params)
    shared: dict[str, Any] = {"group": prim.id, "at": prim.at}
    if prim.color is not None:
        shared["color"] = prim.color
    expanded = [child.model_copy(update=shared) for child in children]
    if prim.label is not None:
        expanded[0] = expanded[0].model_copy(update={"label": prim.label})
    return expanded


def expand_step(step: Step) -> Step:
    draw: list[Any] = []
    for prim in step.draw:
        draw.extend(expand_template(prim) if isinstance(prim, TemplatePrim) else [prim])
    return step.model_copy(update={"draw": draw})


def expand_lesson(lesson: Lesson) -> Lesson:
    """Expand all templates and re-validate, so the result is a fully checked Lesson."""
    expanded = lesson.model_copy(update={"steps": [expand_step(s) for s in lesson.steps]})
    try:
        return Lesson.model_validate(expanded.model_dump())
    except ValidationError as e:
        raise TemplateError(f"expanded lesson is invalid: {e}") from e


def _round_points(points: list[tuple[float, float]]) -> list[Point]:
    return [(r1(x), r1(y)) for x, y in points]
