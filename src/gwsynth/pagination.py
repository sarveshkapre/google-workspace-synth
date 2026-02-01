from __future__ import annotations

import base64
import json
from dataclasses import dataclass
from typing import Any

DEFAULT_LIMIT = 50
MAX_LIMIT = 200


@dataclass(frozen=True)
class Cursor:
    created_at: str
    id: str


def parse_limit(raw: str | None) -> int | None:
    if raw is None:
        return None
    try:
        value = int(raw)
    except ValueError as exc:
        raise ValueError("limit must be an integer") from exc
    if value < 1 or value > MAX_LIMIT:
        raise ValueError(f"limit must be between 1 and {MAX_LIMIT}")
    return value


def encode_cursor(cursor: Cursor) -> str:
    payload = json.dumps(
        {"created_at": cursor.created_at, "id": cursor.id},
        separators=(",", ":"),
    ).encode("utf-8")
    token = base64.urlsafe_b64encode(payload).decode("ascii").rstrip("=")
    return token


def decode_cursor(raw: str) -> Cursor:
    raw = raw.strip()
    if not raw:
        raise ValueError("cursor must be a non-empty string")
    padded = raw + "=" * ((4 - (len(raw) % 4)) % 4)
    try:
        decoded = base64.urlsafe_b64decode(padded.encode("ascii")).decode("utf-8")
    except Exception as exc:  # noqa: BLE001
        raise ValueError("cursor is invalid") from exc
    try:
        obj = json.loads(decoded)
    except json.JSONDecodeError as exc:
        raise ValueError("cursor is invalid") from exc
    if not isinstance(obj, dict):
        raise ValueError("cursor is invalid")
    created_at = obj.get("created_at")
    item_id = obj.get("id")
    if not isinstance(created_at, str) or not created_at:
        raise ValueError("cursor is invalid")
    if not isinstance(item_id, str) or not item_id:
        raise ValueError("cursor is invalid")
    return Cursor(created_at=created_at, id=item_id)


def normalize_json_object(value: Any, label: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ValueError(f"{label} must be an object")
    return value
