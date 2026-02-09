from __future__ import annotations

from gwsynth.real.google_drive import (
    _app_properties_query,
    build_app_properties,
    escape_drive_query_string,
)


def test_build_app_properties_includes_required_fields():
    props = build_app_properties(
        run_name="run",
        stable_id="id",
        kind="doc",
        path="path",
        prompt_version="v1",
        content_hash="hash",
    )
    assert props["gwsynth_run"] == "run"
    assert props["gwsynth_id"] == "id"
    assert props["gwsynth_kind"] == "doc"
    assert props["gwsynth_path"] == "path"
    assert props["gwsynth_prompt_version"] == "v1"
    assert props["gwsynth_content_hash"] == "hash"


def test_escape_drive_query_string_escapes_quotes_and_backslashes():
    assert escape_drive_query_string("O'Hara") == "O\\'Hara"
    assert escape_drive_query_string(r"c:\\tmp\\x") == r"c:\\\\tmp\\\\x"


def test_app_properties_query_is_deterministic_and_escaped():
    query = _app_properties_query({"b": "two", "a": "O'Hara"})
    assert "key='a'" in query
    assert "value='O\\'Hara'" in query
    # Sorted ordering should put 'a' before 'b'.
    assert query.index("key='a'") < query.index("key='b'")
