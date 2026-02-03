from __future__ import annotations

from gwsynth.real.google_drive import build_app_properties


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
