"""Authored, offline physics lessons. JSON stores Source + generation-draft fields.

Keep placeholders and signed metadata in the files so every load can run the
same teaching/sign checks as generation, without an LLM or a route dependency.
"""

import json
import re
import unicodedata
from pathlib import Path
from uuid import NAMESPACE_URL, uuid5

from app.lesson.draft import LessonDraft
from app.lesson.lint import LintState, extract_givens
from app.lesson.models import Lesson, Source
from app.lesson.pipeline import LessonError
from app.lesson.stepcheck import LessonState, check_step, commit

_ROOT = Path(__file__).parent
_TOPICS = {
    "kinematics_1d": ("1d kinematics", "one dimensional kinematics", "constant acceleration"),
    "projectile_motion": ("projectile motion", "projectile"),
    "incline_friction": ("incline with friction", "inclined plane", "incline", "incline friction"),
    "circular_motion": ("circular motion", "centripetal force", "centripetal acceleration"),
    "work_energy": ("work energy theorem", "work energy"),
    "collision_1d": ("1d collision", "inelastic collision", "momentum", "collision"),
    "torque_equilibrium": ("rotational equilibrium", "torque", "torque equilibrium"),
    "spring_shm": ("spring shm", "spring", "simple harmonic motion"),
    "simple_pendulum": ("simple pendulum", "pendulum"),
    "coulomb_law": ("coulomb s law", "coulomb law", "coulomb"),
    "point_charge_field": ("field of a point charge", "point charge field", "point charge"),
    "gauss_line": ("gauss s law for a line charge", "gauss line", "line charge"),
    "gauss_plane": ("gauss s law for a plane", "gauss plane", "charged plane", "infinite sheet"),
    "capacitor_potential": ("parallel plate capacitor", "capacitor", "electric potential"),
    "kirchhoff_two_loop": ("kirchhoff", "two loop circuit", "kirchhoff s two loop circuit"),
    "magnetic_force": ("magnetic force on a moving charge", "magnetic force", "lorentz force"),
    "faraday_rod": ("faraday", "moving rod", "motional emf"),
    "string_wave": ("wave speed on a string", "string wave", "wave speed"),
    "snell_law": ("snell s law", "snell", "refraction"),
    "converging_lens": ("thin converging lens", "converging lens", "thin lens"),
}


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


def find_library_lesson(text: str) -> Lesson | None:
    """Match a topic phrase, returning a fresh, fully checked worked example.

    Source describes this example's givens; this is topic lookup, not a solver for
    arbitrary user-supplied numbers. Ambiguous multi-topic requests return None.
    """
    query = f" {_normalize(text)} "
    matches = {
        topic
        for topic, aliases in _TOPICS.items()
        if any(f" {alias} " in query for alias in aliases)
    }
    if len(matches) != 1:
        return None
    return _load_lesson(_ROOT / f"{matches.pop()}.json")
