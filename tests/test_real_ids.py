from __future__ import annotations

from gwsynth.real.stable_ids import content_hash, stable_uuid


def test_stable_uuid_deterministic():
    value1 = stable_uuid("run", "doc", "key")
    value2 = stable_uuid("run", "doc", "key")
    assert value1 == value2
    assert stable_uuid("run", "doc", "key2") != value1


def test_content_hash_stable():
    assert content_hash("hello") == content_hash(" hello ")
