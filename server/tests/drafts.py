"""Builders for lesson drafts (the model's output format) used across tests."""

import json
from typing import Any

SOURCE_TEXT = (
    "A point charge of 3 nC sits at the center of a sphere of radius 0.2 m. "
    "Find the electric flux through the sphere."
)


def item(
    id: str,
    type: str,
    num: dict[str, float] | None = None,
    txt: dict[str, str] | None = None,
    pts: list[list[float]] | None = None,
    color: str = "ink",
    label: str = "",
    at: float = 0.5,
) -> dict[str, Any]:
    return {
        "id": id,
        "type": type,
        "color": color,
        "label": label,
        "at": at,
        "num": [{"k": k, "v": v} for k, v in (num or {}).items()],
        "txt": [{"k": k, "v": v} for k, v in (txt or {}).items()],
        "pts": pts or [],
    }


def symbol(id: str, latex: str, meaning: str, unit: str, y: float) -> dict[str, Any]:
    return item(
        id, "symbol", {"x": 740, "y": y}, {"symbol": latex, "meaning": meaning, "unit": unit}
    )


def math(id: str, latex: str, y: float = 300) -> dict[str, Any]:
    return item(id, "math", {"x": 740, "y": y}, {"latex": latex}, color="accent")


def calc(
    id: str, expr: str, values: dict[str, float], expected: float, unit: str, unit_spoken: str
) -> dict[str, Any]:
    return {
        "id": id,
        "expr": expr,
        "values": [{"name": k, "value": v} for k, v in values.items()],
        "expected": expected,
        "unit": unit,
        "unit_spoken": unit_spoken,
    }


def step(
    id: str,
    say: str,
    draw: list[dict[str, Any]] | None = None,
    kind: str = "explain",
    calcs: list[dict[str, Any]] | None = None,
    checkpoint: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return {
        "id": id,
        "kind": kind,
        "calcs": calcs or [],
        "say": say,
        "subtitles": {"uz": "Tarjima.", "ru": "Перевод."},
        "draw": draw or [],
        "checkpoints": [checkpoint] if checkpoint else [],
    }


def choice(question: str = "What happens to the flux?", answer: str = "1") -> dict[str, Any]:
    return {
        "question": question,
        "type": "choice",
        "choices": ["doubles", "stays the same", "halves"],
        "answer": answer,
        "hint": "Count the lines.",
        "reexplain_hint": "Picture a bigger bubble.",
    }


FLUX = calc(
    "c1",
    "q/eps0",
    {"q": 3e-9, "eps0": 8.854e-12},
    338.83,
    "N*m**2/C",
    "newton meters squared per coulomb",
)


def good_steps() -> list[dict[str, Any]]:
    return [
        step(
            "s1",
            "Here is our point charge of 3 nanocoulombs at the centre.",
            [
                item("q1", "point_charge", {"x": 300, "y": 500}, {"sign": "+", "name": "Q"}),
                symbol("sym-q", "Q", "charge inside", "C", 60),
            ],
        ),
        step(
            "s2",
            "Flux counts the field lines through a closed surface.",
            [
                symbol("sym-phi", r"\Phi", "electric flux", "N·m²/C", 105),
                symbol("sym-eps", r"\varepsilon_0", "permittivity of free space", "C²/(N·m²)", 150),
                math("law", r"\Phi = \frac{Q}{\varepsilon_0}"),
            ],
        ),
        step(
            "s3",
            "Your turn: a bigger sphere around the same charge.",
            kind="checkpoint",
            checkpoint=choice(),
        ),
        step(
            "s4",
            "So the flux is {c1}, whatever the radius.",
            [math("value", r"\Phi = {c1}", 360)],
            calcs=[FLUX],
        ),
        step(
            "s5",
            "Flux depends only on the charge inside.",
            kind="summary",
            draw=[item("hl", "highlight", txt={"target_id": "law"})],
        ),
    ]


def draft_json(steps: list[dict[str, Any]] | None = None, title: str = "Flux") -> str:
    return json.dumps(
        {"title": title, "level": "simple", "steps": good_steps() if steps is None else steps},
        ensure_ascii=False,
    )
