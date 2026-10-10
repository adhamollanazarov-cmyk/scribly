import json

import pytest

from app.lesson.stream_parse import StepStream
from tests.drafts import draft_json, good_steps


def feed_all(text: str, size: int) -> tuple[list[dict], list[dict], dict]:  # type: ignore[type-arg]
    parser = StepStream()
    headers, steps = [], []
    for start in range(0, len(text), size):
        header, new = parser.feed(text[start : start + size])
        headers += [header] if header else []
        steps += new
    header, new, data = parser.finish()
    headers += [header] if header else []
    return headers, steps + new, data


@pytest.mark.parametrize("size", [1, 7, 64, 10_000])
def test_every_step_is_emitted_once_in_order(size: int) -> None:
    headers, steps, data = feed_all(draft_json(), size)

    assert headers == [{"title": "Flux", "level": "simple"}]
    assert steps == good_steps()
    assert data["steps"] == steps


def test_a_step_is_emitted_when_the_next_one_starts() -> None:
    text = draft_json()
    parser = StepStream()
    second_step_start = text.index('{"id": "s2"')
    header, steps = parser.feed(text[: second_step_start + 3])

    assert header == {"title": "Flux", "level": "simple"}
    assert [s["id"] for s in steps] == ["s1"]


def test_header_waits_until_the_title_is_complete() -> None:
    parser = StepStream()
    assert parser.feed('{"title": "Gauss') == (None, [])
    header, _ = parser.feed('\'s law", "level": "simple", "steps": [')
    assert header == {"title": "Gauss's law", "level": "simple"}


def test_escapes_and_newlines_inside_strings_are_handled() -> None:
    steps = good_steps()
    steps[0]["say"] = 'A "quoted"\nline with \\ backslash and { braces }.'
    _, out, _ = feed_all(json.dumps({"title": "T", "level": "simple", "steps": steps}), 5)
    assert out[0]["say"] == steps[0]["say"]


def test_incomplete_json_at_the_end_is_an_error() -> None:
    parser = StepStream()
    parser.feed(draft_json()[:-50])
    with pytest.raises(ValueError):
        parser.finish()
