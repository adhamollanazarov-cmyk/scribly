"""Regenerate shared/streams/*.json and shared/library_topics.json.

Run from server/: uv run python -m scripts.gen_streams
"""

from app.lesson.stream_export import STREAMS_DIR, write_streams

if __name__ == "__main__":
    names = write_streams()
    print(f"wrote {len(names)} stream(s) to {STREAMS_DIR}: {', '.join(names)}")
