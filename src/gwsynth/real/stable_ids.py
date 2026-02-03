from __future__ import annotations

import hashlib
import uuid

NAMESPACE = uuid.UUID("2e6b18fd-1f64-4f75-9f3d-1a4e2a4e5f6c")


def stable_uuid(run_name: str, object_type: str, canonical_key: str) -> str:
    name = f"{run_name}:{object_type}:{canonical_key}"
    return str(uuid.uuid5(NAMESPACE, name))


def sha256_hex(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def content_hash(text: str) -> str:
    return sha256_hex(text.strip())
