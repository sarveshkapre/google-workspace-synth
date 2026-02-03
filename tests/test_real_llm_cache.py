from __future__ import annotations

from gwsynth.real.google_docs import DocContent, DocSection
from gwsynth.real.llm_openai import cache_key, load_cache, write_cache


def test_llm_cache_round_trip(tmp_path):
    content = DocContent(
        title="Title",
        summary="Summary",
        sections=(
            DocSection(heading="H1", paragraphs=("P1",), bullets=("B1", "B2")),
        ),
        metadata=("meta",),
    )
    key = cache_key(
        model="gpt-5.2",
        temperature=0.4,
        prompt_version="v1",
        stable_doc_id="doc-1",
        prompt="prompt",
    )
    write_cache(str(tmp_path), key, content, raw_text="raw")
    cached = load_cache(str(tmp_path), key)
    assert cached is not None
    assert cached.title == "Title"
    assert cached.sections[0].heading == "H1"
