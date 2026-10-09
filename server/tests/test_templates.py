import math
from typing import Any

import pytest

from app.lesson.fixtures import load_fixture
from app.lesson.models import (
    ArrowPrim,
    CirclePrim,
    CurvePrim,
    Lesson,
    LinePrim,
    PolylinePrim,
    TemplatePrim,
    VectorPrim,
    check_references,
)
from app.lesson.templates import TemplateError, expand_lesson, expand_template


def template(kind: str, tid: str = "t1", /, **params: Any) -> TemplatePrim:
    return TemplatePrim(id=tid, type="template", name=kind, params=params)


def ids(children: list[Any]) -> list[str]:
    return [c.id for c in children]


def test_point_charge_positive() -> None:
    out = expand_template(template("point_charge", "q1", x=450, y=500, r=18, name="Q"))

    assert ids(out) == ["q1-charge", "q1-sign-h", "q1-sign-v"]
    charge = out[0]
    assert isinstance(charge, CirclePrim)
    assert (charge.cx, charge.cy, charge.r, charge.color, charge.label) == (
        450, 500, 18, "charge_pos", "Q",
    )  # fmt: skip
    assert all(c.group == "q1" for c in out)


def test_point_charge_negative_has_no_vertical_bar() -> None:
    out = expand_template(template("point_charge", x=0, y=0, sign="-"))

    assert ids(out) == ["t1-charge", "t1-sign-h"]
    assert out[0].color == "charge_neg"  # type: ignore[attr-defined]


def test_radial_field_lines_point_outward_evenly() -> None:
    out = expand_template(template("radial_field_lines", x=100, y=100, n=4, r_start=10, r_end=50))

    assert ids(out) == ["t1-1", "t1-2", "t1-3", "t1-4"]
    first, second = out[0], out[1]
    assert isinstance(first, ArrowPrim) and isinstance(second, ArrowPrim)
    assert (first.x1, first.y1, first.x2, first.y2) == (110, 100, 150, 100)  # 0 deg: right
    assert (second.x1, second.y1, second.x2, second.y2) == (100, 90, 100, 50)  # 90 deg: up
    assert all(c.color == "field" for c in out)  # type: ignore[attr-defined]


def test_radial_field_lines_inward_reverse_direction() -> None:
    out = expand_template(
        template("radial_field_lines", x=0, y=0, n=1, r_start=10, r_end=50, direction="in")
    )

    arrow = out[0]
    assert isinstance(arrow, ArrowPrim)
    assert (arrow.x1, arrow.x2) == (50, 10)


def test_radial_field_lines_rejects_inverted_radii() -> None:
    with pytest.raises(TemplateError, match="r_end > r_start"):
        expand_template(template("radial_field_lines", x=0, y=0, r_start=50, r_end=10))


def test_gaussian_sphere_is_a_dashed_surface_circle() -> None:
    out = expand_template(template("gaussian_sphere", "surface1", cx=450, cy=500, r=130))

    assert ids(out) == ["surface1-sphere"]
    sphere = out[0]
    assert isinstance(sphere, CirclePrim)
    assert sphere.dashed and sphere.color == "surface" and sphere.r == 130


def test_charged_plane_vertical() -> None:
    out = expand_template(
        template("charged_plane", "p", x=500, y=500, length=400, n=2, field_length=100)
    )

    assert ids(out) == ["p-plane", "p-q1", "p-e1", "p-e2", "p-q2", "p-e3", "p-e4"]
    plane = out[0]
    assert isinstance(plane, LinePrim)
    assert (plane.x1, plane.y1, plane.x2, plane.y2) == (500, 300, 500, 700)
    right, left = out[2], out[3]
    assert isinstance(right, ArrowPrim) and isinstance(left, ArrowPrim)
    assert right.x2 > right.x1 > 500  # field points away from a positive plane
    assert left.x2 < left.x1 < 500


def test_charged_plane_negative_points_inward() -> None:
    out = expand_template(template("charged_plane", x=0, y=0, n=1, sign="-"))

    arrow = out[2]
    assert isinstance(arrow, ArrowPrim)
    assert abs(arrow.x2) < abs(arrow.x1)


def test_incline_block_geometry() -> None:
    out = expand_template(template("incline_block", x=100, y=600, base=400, angle_deg=30))

    assert ids(out) == ["t1-incline", "t1-block", "t1-angle"]
    incline, block = out[0], out[1]
    assert isinstance(incline, PolylinePrim) and isinstance(block, PolylinePrim)
    height = 400 * math.tan(math.radians(30))
    assert incline.points[:2] == [(100, 600), (500, 600)]
    assert incline.points[2] == pytest.approx((100, 600 - height), abs=0.1)
    # The block's base lies on the slope: both corners satisfy the slope line equation.
    for x, y in block.points[:2]:
        assert y == pytest.approx(600 - (500 - x) * math.tan(math.radians(30)), abs=0.2)


def test_incline_block_rejects_block_longer_than_slope() -> None:
    with pytest.raises(TemplateError, match="longer than the slope"):
        expand_template(template("incline_block", x=0, y=0, base=50, angle_deg=30, block=100))


def test_free_body_vectors_follow_angles() -> None:
    forces = [
        {"name": "W", "angle_deg": 270, "length": 100},
        {"name": "N", "angle_deg": 90, "length": 100},
    ]
    out = expand_template(template("free_body", x=300, y=300, forces=forces))

    assert ids(out) == ["t1-body", "t1-f1", "t1-f2"]
    weight, normal = out[1], out[2]
    assert isinstance(weight, VectorPrim) and isinstance(normal, VectorPrim)
    assert weight.from_ == (300, 300) and weight.to == (300, 400)  # down on screen
    assert normal.to == (300, 200) and normal.name == "N"


def test_axes_plot_maps_curve_into_the_box() -> None:
    out = expand_template(
        template("axes_plot", x=100, y=100, w=200, h=100, expr="x^2", x_min=0, x_max=2,
                 samples=3)
    )  # fmt: skip

    assert ids(out) == ["t1-axes", "t1-curve"]
    curve = out[1]
    assert isinstance(curve, CurvePrim)
    # y range is 0..4 from the samples: (0,0) bottom-left, (1,1), (2,4) top-right.
    assert curve.points == [(100, 200), (200, 175), (300, 100)]


def test_axes_plot_rejects_unsafe_expression() -> None:
    with pytest.raises(TemplateError, match="axes_plot"):
        expand_template(
            template("axes_plot", x=0, y=0, w=10, h=10, expr="__import__('os')", x_min=0,
                     x_max=1)
        )  # fmt: skip


def test_unknown_template_and_bad_params_are_errors() -> None:
    with pytest.raises(TemplateError, match="unknown template"):
        expand_template(template("hexagon"))
    with pytest.raises(TemplateError, match="bad params"):
        expand_template(template("gaussian_sphere", cx=0, cy=0, r=-5))
    with pytest.raises(TemplateError, match="bad params"):
        expand_template(template("gaussian_sphere", cx=0, cy=0, r=5, radius=5))


def test_template_at_color_and_label_are_passed_to_children() -> None:
    prim = TemplatePrim(
        id="s", type="template", name="gaussian_sphere", params={"cx": 0, "cy": 0, "r": 9},
        at=0.4, color="highlight", label="S",
    )  # fmt: skip

    (child,) = expand_template(prim)

    assert (child.at, child.color, child.label) == (0.4, "highlight", "S")  # type: ignore[attr-defined]


def test_expansion_is_deterministic() -> None:
    lesson = Lesson.model_validate(load_fixture("gauss_law"))

    assert expand_lesson(lesson) == expand_lesson(lesson)


def test_expanded_gauss_lesson_has_no_templates_and_valid_references() -> None:
    expanded = expand_lesson(Lesson.model_validate(load_fixture("gauss_law")))
    prims = [p for s in expanded.steps for p in s.draw]

    assert not any(isinstance(p, TemplatePrim) for p in prims)
    assert check_references(expanded) == []
    assert len([p for p in prims if p.group == "lines1"]) == 12
