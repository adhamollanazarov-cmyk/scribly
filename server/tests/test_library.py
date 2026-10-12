"""Offline library checks plus independent plain-Python reference calculations.

The reference uses fixed problem data, never calc.expr, calc.values, SymPy, or
the result ledger. Every numeric answer, including intermediate results, is
covered. Conservation checks provide a second way to check coupled problems.
"""

import json
import math
from pathlib import Path

import pytest

from app.lesson.direction import physical
from app.lesson.models import Lesson, check_references
from app.lesson.pipeline import LessonError
from app.lesson.verify import verify_lesson
from app.library import _load_lesson, find_library_lesson

ROOT = Path(__file__).resolve().parents[1] / "app" / "library"
PATHS = sorted(ROOT.glob("*.json"))


def references() -> dict[str, list[float]]:
    # Independently derive time by vertical symmetry, then horizontal travel.
    vx, vy = 20 * math.cos(math.radians(30)), 20 * math.sin(math.radians(30))
    flight = 2 * vy / 9.8
    normal = 2 * 9.8 * math.cos(math.radians(30))
    # Solve two loop equations via a 2x2 determinant, not the node-voltage formula.
    # 8*J1 + 6*J2 = 12; 6*J1 + 9*J2 = 6. J1/J2 go through sources B->A.
    determinant = 8 * 9 - 6 * 6
    j1 = (12 * 9 - 6 * 6) / determinant
    j2 = (8 * 6 - 6 * 12) / determinant
    load_current = j1 + j2
    spring_period = 2 * math.pi * math.sqrt(0.5 / 200)
    pendulum_frequency = math.sqrt(9.8 / 1) / (2 * math.pi)
    string_speed = math.sqrt(80 / 0.005)
    image_distance = 0.1 * 0.3 / (0.3 - 0.1)
    return {
        "kinematics_1d": [3 + 2 * 4, ((3 + (3 + 2 * 4)) / 2) * 4],
        "projectile_motion": [flight, vx * flight],
        "incline_friction": [normal, (2 * 9.8 * math.sin(math.radians(30)) - 0.2 * normal) / 2],
        "circular_motion": [4**2 / 2, 0.5 * 4**2 / 2],
        "work_energy": [4 * 5, math.sqrt(2 * (2 * 3**2 / 2 + 4 * 5) / 2)],
        "collision_1d": [2 * 3 + 1 * 0, (2 * 3 + 1 * 0) / (2 + 1)],
        "torque_equilibrium": [-30 * 2, (30 * 2) / 3],
        "spring_shm": [2 * math.pi / spring_period, math.sqrt(200 * 0.1**2 / 0.5)],
        "simple_pendulum": [1 / pendulum_frequency, pendulum_frequency],
        "coulomb_law": [8.99e9 * 2e-6 * 3e-6 / 0.3**2],
        "point_charge_field": [8.99e9 * 4e-9 / 0.2**2],
        "gauss_line": [(2e-9 * 1) / (8.854e-12 * (2 * math.pi * 0.1 * 1))],
        "gauss_plane": [(3e-9 * 1) / (8.854e-12 * 2 * 1)],
        "capacitor_potential": [
            12 / 0.001,
            8.854e-12 * 0.02 / 0.001,
            (8.854e-12 * 0.02 / 0.001) * 12,
        ],
        "kirchhoff_two_loop": [6 * load_current, -j1, -j2, load_current],
        "magnetic_force": [2e-6 * 3e4 * 0.5],
        "faraday_rod": [0.5 * (0.4 * 3), 0.5 * (0.4 * 3) / 2],
        "string_wave": [string_speed, string_speed / 50],
        "snell_law": [math.degrees(math.asin(math.sin(math.radians(30)) / 1.5))],
        "converging_lens": [image_distance, -image_distance / 0.3],
    }


ANSWERS = references()
NUMERIC_CASES = [
    (key, i, value) for key, values in ANSWERS.items() for i, value in enumerate(values, 1)
]


def test_exact_topic_inventory() -> None:
    assert len(PATHS) == 20
    assert {p.stem for p in PATHS} == ANSWERS.keys()


@pytest.mark.parametrize("path", PATHS, ids=lambda p: p.stem)
def test_full_pipeline(path: Path) -> None:
    lesson = _load_lesson(path)
    assert Lesson.model_validate_json(lesson.model_dump_json()) == lesson
    assert not check_references(lesson)
    assert all(result.ok for result in verify_lesson(lesson))
    assert len(lesson.calcs) == len(ANSWERS[path.stem])
    assert all(c.used_in_steps for c in lesson.calcs)
    assert all(
        s.warning is None and s.subtitles.uz and len(s.say.split()) <= 30 for s in lesson.steps
    )
    assert all(p.type not in ("template", "plot") for s in lesson.steps for p in s.draw)
    checkpoints = [s.checkpoint for s in lesson.steps if s.checkpoint]
    assert len(checkpoints) >= 2
    assert all(cp.hint and cp.reexplain_hint and cp.hint != cp.reexplain_hint for cp in checkpoints)
    assert checkpoints[-1].answer == pytest.approx(ANSWERS[path.stem][0], rel=0.005)


@pytest.mark.parametrize(
    "key,index,answer", NUMERIC_CASES, ids=[f"{key}-c{i}" for key, i, _ in NUMERIC_CASES]
)
def test_every_numeric_answer_independently(key: str, index: int, answer: float) -> None:
    lesson = _load_lesson(ROOT / f"{key}.json")
    calc = next(c for c in lesson.calcs if c.id == f"c{index}")
    assert calc.expected == pytest.approx(answer, rel=1e-10, abs=1e-20)
    result = next(r for r in verify_lesson(lesson) if r.calc_id == calc.id)
    assert result.value == pytest.approx(answer, rel=1e-10, abs=1e-20)


@pytest.mark.parametrize("key", ANSWERS)
def test_lookup_by_title_and_filename(key: str) -> None:
    lesson = _load_lesson(ROOT / f"{key}.json")
    found = find_library_lesson(f"Please explain {lesson.title.upper()}.")
    assert found is not None and found.id == lesson.id


@pytest.mark.parametrize(
    "query,key",
    [
        ("Newton's 2nd law on an incline with friction", "incline_friction"),
        ("Gauss’s law for a plane", "gauss_plane"),
        ("Teach me GAUSS'S LAW FOR A LINE CHARGE", "gauss_line"),
        ("electric potential and a parallel-plate capacitor", "capacitor_potential"),
        ("momentum and a 1D collision", "collision_1d"),
        ("spring SHM", "spring_shm"),
    ],
)
def test_lookup_phrases(query: str, key: str) -> None:
    found = find_library_lesson(query)
    assert found is not None and found.title == _load_lesson(ROOT / f"{key}.json").title


@pytest.mark.parametrize(
    "query",
    [
        "",
        "biology",
        "springboard",
        "torques",
        "Gauss law",
        "compare spring SHM and simple pendulum",
    ],
)
def test_unknown_substrings_and_ambiguous_requests(query: str) -> None:
    assert find_library_lesson(query) is None


def test_lookup_returns_isolated_objects() -> None:
    first = find_library_lesson("projectile")
    second = find_library_lesson("projectile")
    assert first is not None and second is not None
    first.steps.clear()
    assert second.steps and first.id == second.id


def test_physics_conservation_and_directions() -> None:
    values = ANSWERS["kirchhoff_two_loop"]
    voltage, i1, i2, i3 = values
    assert math.isclose(i1 + i2 + i3, 0, abs_tol=1e-14)
    assert math.isclose(-(12 * i1 + 6 * i2), 2 * i1**2 + 3 * i2**2 + 6 * i3**2)
    assert math.isclose(voltage, 12 + 2 * i1)
    assert math.isclose(voltage, 6 + 3 * i2)
    assert math.isclose(2 * 3, (2 + 1) * ANSWERS["collision_1d"][1])
    assert math.isclose(ANSWERS["torque_equilibrium"][0] + 3 * ANSWERS["torque_equilibrium"][1], 0)
    for key, calc_id, direction in [
        ("incline_friction", "c2", "down the slope"),
        ("torque_equilibrium", "c1", "cw"),
        ("kirchhoff_two_loop", "c2", "b->a"),
        ("kirchhoff_two_loop", "c3", "a->b"),
        ("kirchhoff_two_loop", "c4", "a->b"),
        ("magnetic_force", "c1", "+y"),
        ("converging_lens", "c2", "-y"),
    ]:
        raw = json.loads((ROOT / f"{key}.json").read_text(encoding="utf-8"))
        calc = next(c for s in raw["steps"] for c in s["calcs"] if c["id"] == calc_id)
        assert physical(calc["expected"], calc["positive"]) == direction


@pytest.mark.parametrize("defect", ["number", "symbol", "sign", "calc", "template"])
def test_loader_rejects_invalid_authored_content(tmp_path: Path, defect: str) -> None:
    raw = json.loads((ROOT / "projectile_motion.json").read_text(encoding="utf-8"))
    if defect == "number":
        raw["steps"][0]["say"] = "The answer is 123.456 meters."
    elif defect == "symbol":
        raw["steps"][1]["draw"] = []
    elif defect == "sign":
        raw["steps"][5]["calcs"][0]["positive"] = "-x"
    elif defect == "calc":
        raw["steps"][4]["calcs"][0]["expected"] = 123
    else:
        raw["steps"][0]["draw"][1]["num"].append({"k": "samples", "v": 999})
    path = tmp_path / "broken.json"
    path.write_text(json.dumps(raw), encoding="utf-8")
    with pytest.raises(LessonError):
        _load_lesson(path)
