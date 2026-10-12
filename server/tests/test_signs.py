"""Sign conventions: direction vocabulary, and the one-convention-per-lesson step lint."""

from typing import Any

import pytest

from app.lesson.direction import normalize, opposite, physical
from app.lesson.lint import LintState
from app.lesson.models import Source
from app.lesson.stepcheck import LessonState, check_step, commit
from tests.drafts import calc, item, step

SOURCE = Source(type="problem", text="Charges q1 = 2 nC and q2 = -3 nC are 0.3 m apart.")
PLUS_X = item("conv", "arrow", {"x1": 100, "y1": 900, "x2": 300, "y2": 900}, label="+x", at=0)


@pytest.mark.parametrize(
    ("text", "canonical"),
    [
        ("+x", "+x"),
        (" X ", "+x"),
        ("positive x direction", "+x"),
        ("−y", "-y"),
        ("up", "+y"),
        ("left", "-x"),
        ("A->B", "a->b"),
        ("from A to B", "a->b"),
        ("A → B", "a->b"),
        ("clockwise", "cw"),
        ("Down the incline", "down the slope"),
        ("toward q2", "toward q2"),
        ("into page", "into the page"),
        ("", ""),
    ],
)
def test_directions_are_normalized(text: str, canonical: str) -> None:
    assert normalize(text) == canonical


@pytest.mark.parametrize("text", ["sideways", "A->A", "into", "north-ish", "x y"])
def test_unreadable_directions_are_none(text: str) -> None:
    assert normalize(text) is None


@pytest.mark.parametrize(
    ("direction", "other"),
    [
        ("+x", "-x"),
        ("a->b", "b->a"),
        ("cw", "ccw"),
        ("down the slope", "up the slope"),
        ("toward q2", "away from q2"),
        ("into the page", "out of the page"),
    ],
)
def test_opposites_are_symmetric(direction: str, other: str) -> None:
    assert opposite(direction) == other
    assert opposite(other) == direction


def test_physical_direction_follows_the_sign() -> None:
    assert physical(0.45, "A->B") == "a->b"
    assert physical(-0.45, "A->B") == "b->a"
    assert physical(-2.0, "+x") == "-x"
    assert physical(0.0, "+x") is None
    assert physical(3.0, "") is None


def check(raw: dict[str, Any], state: LessonState | None = None) -> list[str]:
    context = state or LessonState(SOURCE, LintState([]))
    return [v.message for v in check_step(raw, context).violations if v.rule == "sign"]


def force(id: str, positive: str, value: float = -0.6) -> dict[str, Any]:
    return calc(id, "F", {"F": value}, value, "N", "newtons", positive)


def test_signed_calc_with_a_drawn_convention_passes_and_carries_its_sign() -> None:
    context = LessonState(SOURCE, LintState([]))
    raw = step(
        "s1", "Right is positive, so the force is {c1}.", [PLUS_X], calcs=[force("c1", "+x")]
    )

    checked = check_step(raw, context)

    assert not checked.violations
    assert checked.entries["c1"].positive == "+x"
    commit(context, checked)
    assert context.lint.conventions == {("lab", "+x")}
    assert context.lint.drawn_conventions == {("lab", "+x")}


def test_signed_calc_needs_a_drawn_convention() -> None:
    messages = check(step("s1", "The force is {c1}.", calcs=[force("c1", "+x")]))
    assert len(messages) == 1 and "does not show the sign convention" in messages[0]


def test_axes_or_a_plus_labelled_vector_also_show_the_convention() -> None:
    axes = item(
        "ax", "axes", {"x": 100, "y": 100, "w": 400, "h": 300}, {"xlabel": "x", "ylabel": "y"}, at=0
    )
    vector = item(
        "v",
        "vector",
        {"x1": 1, "y1": 1, "x2": 9, "y2": 1},
        {"name": "+ (A→B)"},
        color="force",
        at=0,
    )
    for drawing, positive in ((axes, "+x"), (vector, "A->B")):
        assert (
            check(step("s1", "The force is {c1}.", [drawing], calcs=[force("c1", positive)])) == []
        )


def test_unlabelled_arrow_is_not_a_convention() -> None:
    arrow = item("a", "arrow", {"x1": 1, "y1": 1, "x2": 9, "y2": 1}, label="I1")
    assert check(step("s1", "The force is {c1}.", [arrow], calcs=[force("c1", "+x")]))


def test_opposite_conventions_in_one_lesson_are_rejected() -> None:
    raw = step(
        "s1",
        "The currents are {c1} and {c2}.",
        [{**PLUS_X, "label": "+ (A->B)"}],
        calcs=[force("c1", "A->B"), force("c2", "from B to A")],
    )
    messages = check(raw)
    assert any("one sign convention" in message and "c2" in message for message in messages)


def test_opposite_of_an_earlier_step_is_rejected() -> None:
    context = LessonState(SOURCE, LintState([]))
    commit(context, check_step(step("s1", "{c1}.", [PLUS_X], calcs=[force("c1", "+x")]), context))
    assert check(step("s2", "{c2}.", calcs=[force("c2", "-x")]), context)
    assert check(step("s3", "{c3}.", calcs=[force("c3", "+y")]), context)


def test_unreadable_positive_direction_is_sent_back() -> None:
    checked = check_step(
        step("s1", "{c1}.", [PLUS_X], calcs=[force("c1", "sideways")]),
        LessonState(SOURCE, LintState([])),
    )
    assert checked.fatal and not checked.entries
    assert any("readable positive" in v.message for v in checked.violations)


def test_scalar_calcs_need_no_convention() -> None:
    raw = step(
        "s1", "The energy is {c1}.", calcs=[calc("c1", "U", {"U": -2.0}, -2.0, "J", "joules")]
    )
    assert check(raw) == []
