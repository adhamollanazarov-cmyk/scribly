"""Authored, offline physics lessons. JSON stores Source + generation-draft fields.

Keep placeholders and signed metadata in the files so every load can run the
same teaching/sign checks as generation, without an LLM or a route dependency.
"""

import json
import re
import unicodedata
from functools import cache
from pathlib import Path
from uuid import NAMESPACE_URL, uuid5

from app.lesson.draft import LessonDraft
from app.lesson.lint import LintState, extract_givens
from app.lesson.models import Lesson, Source
from app.lesson.pipeline import LessonError
from app.lesson.stepcheck import LessonState, check_step, commit

_ROOT = Path(__file__).parent
# Phrases that name each topic (each lesson's title is added too). No bare generic words:
# "spring", "momentum" or "faraday" also appear in questions about different physics.
_TOPICS = {
    "kinematics_1d": (
        "1d kinematics",
        "one dimensional kinematics",
        "kinematics in one dimension",
        "motion with constant acceleration",
    ),
    "projectile_motion": ("projectile motion",),
    "incline_friction": (
        "incline with friction",
        "inclined plane with friction",
        "friction on an incline",
        "incline friction",
        "inclined plane",
    ),
    "circular_motion": (
        "uniform circular motion",
        "circular motion",
        "centripetal force",
        "centripetal acceleration",
    ),
    "work_energy": ("work energy theorem", "work energy", "work and kinetic energy"),
    "collision_1d": (
        "1d collision",
        "one dimensional collision",
        "collision in one dimension",
        "perfectly inelastic collision",
        "inelastic collision",
    ),
    "torque_equilibrium": ("rotational equilibrium", "torque equilibrium", "torque balance"),
    "spring_shm": (
        "spring shm",
        "mass on a spring",
        "spring mass system",
        "simple harmonic motion",
    ),
    "simple_pendulum": ("simple pendulum",),
    "coulomb_law": (
        "coulomb s law",
        "coulombs law",
        "coulomb law",
        "force between two point charges",
        "force between two charges",
    ),
    "point_charge_field": (
        "field of a point charge",
        "point charge field",
        "electric field of a point charge",
    ),
    "gauss_line": (
        "gauss s law for a line charge",
        "gauss line",
        "infinite line charge",
        "field of a line charge",
        "line charge",
    ),
    "gauss_plane": (
        "gauss s law for a plane",
        "gauss plane",
        "charged plane",
        "infinite sheet",
        "infinite plane of charge",
        "sheet of charge",
        "charged sheet",
    ),
    "capacitor_potential": (
        "parallel plate capacitor",
        "parallel plate capacitors",
        "capacitance of parallel plates",
    ),
    "kirchhoff_two_loop": (
        "kirchhoff s laws",
        "kirchhoff s rules",
        "kirchhoff s law",
        "kirchhoff laws",
        "kirchhoff rules",
        "two loop circuit",
    ),
    "magnetic_force": (
        "magnetic force on a moving charge",
        "magnetic force on a charge",
        "force on a moving charge",
        "charged particle in a magnetic field",
        "lorentz force",
    ),
    "faraday_rod": ("moving rod", "sliding rod", "rod on rails", "motional emf", "faraday s law"),
    "string_wave": (
        "wave speed on a string",
        "waves on a string",
        "wave on a string",
        "string wave",
        "transverse wave on a string",
    ),
    "snell_law": ("snell s law", "snells law", "snell law", "law of refraction"),
    "converging_lens": ("thin converging lens", "converging lens", "convex lens", "thin lens"),
}
# Words that mean the question is about something the worked example does not cover
# (docs/reviews/library.md H1).
_NOT = {
    "projectile_motion": (
        "cliff",
        "building",
        "tower",
        "table",
        "roof",
        "height",
        "air resistance",
        "drag",
    ),
    "incline_friction": ("frictionless", "pulley", "static"),
    "circular_motion": (
        "vertical",
        "banked",
        "non uniform",
        "nonuniform",
        "tangential acceleration",
    ),
    "work_energy": ("power", "potential energy", "spring"),
    "collision_1d": ("elastic", "angular", "photon", "2d", "two dimensional", "explosion"),
    "torque_equilibrium": (
        "current loop",
        "magnetic",
        "motor",
        "angular acceleration",
        "moment of inertia",
    ),
    "spring_shm": ("series", "parallel", "compressed", "energy stored", "damped"),
    "simple_pendulum": ("conical", "physical", "compound", "torsion", "large angle", "damped"),
    "coulomb_law": ("potential energy", "three charges", "field"),
    "point_charge_field": ("flux", "sphere", "gauss", "potential"),
    "gauss_line": ("finite", "ring", "rod of length"),
    "gauss_plane": ("conductor", "conducting", "two plates"),
    "capacitor_potential": ("dielectric", "series", "discharging", "charging", "energy", "rc"),
    "kirchhoff_two_loop": ("radiation", "thermal", "spectroscopy", "diffraction"),
    "magnetic_force": ("wire", "current", "loop", "solenoid"),
    "faraday_rod": (
        "cage",
        "coil",
        "rotating",
        "generator",
        "solenoid",
        "transformer",
        "electrolysis",
    ),
    "string_wave": ("sound", "air", "light", "standing", "harmonic"),
    "snell_law": ("total internal reflection", "critical angle", "prism", "lens"),
    "converging_lens": ("diverging", "concave", "mirror", "two lenses", "combination"),
}
# A number with a unit means a problem with its own data, not a topic: the worked example
# has different givens, so serving it would answer a different question.
_PROBLEM = re.compile(
    r"\d(?:[.,]\d+)?(?:e[-+]?\d+)?\s*(?:°|(?:k?g|mg|m|cm|mm|km|s|ms|min|h|k?n|k?j|k?w|n?c|μc|uc|"
    r"mc|k?v|m?a|ohms?|ω|m?t|k?hz|deg|degrees?|rad|[μunp]?f|ev|m/s|n/m|kg/m)(?![a-z]))"
)


def _normalize(text: str) -> str:
    text = unicodedata.normalize("NFKC", text).casefold()
    return " ".join(re.findall(r"[a-z0-9]+", text))


def _load_lesson(path: Path) -> Lesson:
    raw = json.loads(path.read_text(encoding="utf-8"))
    source = Source.model_validate(raw.pop("source"))
    draft = LessonDraft.model_validate(raw)
    state = LessonState(source=source, lint=LintState(givens=extract_givens(source.text)))
    for step in draft.steps:
        checked = check_step(step.model_dump(), state)
        if checked.violations or checked.step is None:
            details = "; ".join(v.message for v in checked.violations)
            raise LessonError(f"Library lesson {path.stem}/{step.id}: {details}")
        commit(state, checked)
    return Lesson(
        id=str(uuid5(NAMESPACE_URL, f"scribbly/library/{path.stem}/v1")),
        title=draft.title,
        level=draft.level,
        source=source,
        steps=state.steps,
        calcs=state.calcs,
    )


@cache
def _aliases(topic: str) -> tuple[str, ...]:
    raw = json.loads((_ROOT / f"{topic}.json").read_text(encoding="utf-8"))
    return (_normalize(raw["title"]), *_TOPICS[topic])


def find_library_lesson(text: str) -> Lesson | None:
    """Match a topic phrase, returning a fresh, fully checked worked example.

    Source describes this example's givens; this is topic lookup, not a solver: text with
    its own numbers and units returns None, as do questions about neighbouring physics
    (negative keywords) and ambiguous multi-topic requests.
    """
    if _PROBLEM.search(unicodedata.normalize("NFKC", text).casefold()):
        return None
    query = f" {_normalize(text)} "
    matches = {
        topic
        for topic in _TOPICS
        if any(f" {alias} " in query for alias in _aliases(topic))
        and not any(f" {word} " in query for word in _NOT.get(topic, ()))
    }
    if len(matches) != 1:
        return None
    return _load_lesson(_ROOT / f"{matches.pop()}.json")
