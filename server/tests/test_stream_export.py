import json
from contextlib import closing
from pathlib import Path

import pytest

from app.lesson.fixtures import DEFAULT_FIXTURE, fixture_for_text, fixture_names, load_fixture
from app.lesson.models import StreamedStep
from app.lesson.stream_export import STREAMS_DIR, TOPICS_FILE, render_stream, render_topics
from tests.test_lessons_api import FakeTTS, make_client, parse_sse

STALE = "shared/streams is stale. Run in server/: uv run python -m scripts.gen_streams"


@pytest.mark.parametrize("name", fixture_names())
def test_shared_stream_is_up_to_date(name: str) -> None:
    path = STREAMS_DIR / f"{name}.json"

    assert path.is_file(), STALE
    assert path.read_text(encoding="utf-8").replace("\r\n", "\n") == render_stream(name), STALE


def test_shared_library_topics_are_up_to_date() -> None:
    assert TOPICS_FILE.is_file(), STALE
    text = TOPICS_FILE.read_text(encoding="utf-8").replace("\r\n", "\n")
    assert text == render_topics(), STALE
    assert len(json.loads(render_topics())) == 20


def test_no_stream_without_a_fixture() -> None:
    assert sorted(p.stem for p in STREAMS_DIR.glob("*.json")) == fixture_names()


@pytest.mark.parametrize("name", fixture_names())
def test_stream_is_meta_steps_done_with_audio(name: str) -> None:
    events = json.loads(render_stream(name))
    kinds = [e["event"] for e in events]

    assert kinds[0] == "meta" and kinds[-1] == "done"
    assert set(kinds[1:-1]) == {"step"}
    assert events[0]["data"]["step_count"] == len(kinds) - 2
    for event in events[1:-1]:
        step = StreamedStep.model_validate(event["data"])
        assert step.audio_url is not None and step.audio_url.startswith("/audio/")


@pytest.mark.parametrize("name", fixture_names())
def test_each_fixture_is_found_by_its_source_text(name: str) -> None:
    text = load_fixture(name)["source"]["text"]

    assert fixture_for_text(text) == name
    assert fixture_for_text("  " + text.upper().replace(" ", "\n ") + " ") == name


def test_unknown_text_falls_back_to_the_default_fixture() -> None:
    assert fixture_for_text("Explain magnetism") == DEFAULT_FIXTURE


def test_mock_route_serves_the_fixture_matching_the_request(tmp_path: Path) -> None:
    raw = load_fixture("circ_series")
    with closing(make_client(tmp_path, FakeTTS())) as client:
        response = client.post("/lessons", json={"type": "problem", "text": raw["source"]["text"]})

    events = parse_sse(response.text)
    assert events[0] == ("meta", json.loads(render_stream("circ_series"))[0]["data"])
    assert [name for name, _ in events].count("step") == len(raw["steps"])


def test_mock_route_serves_a_library_topic_after_the_fixtures(tmp_path: Path) -> None:
    with closing(make_client(tmp_path, FakeTTS())) as client:
        library = client.post("/lessons", json={"type": "topic", "text": "Snell’s law"})
        fixture = client.post("/lessons", json={"type": "topic", "text": "Explain magnetism"})

    assert parse_sse(library.text)[0][1]["title"] == "Snell’s law"
    assert parse_sse(fixture.text)[0][1]["title"] == "Gauss's law"
