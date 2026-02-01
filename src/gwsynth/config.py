from __future__ import annotations

import os
from pathlib import Path

DEFAULT_DB_PATH = "./data/gwsynth.db"
DEFAULT_MAX_REQUEST_BYTES = 2_000_000


def db_path() -> str:
    path = os.environ.get("GWSYNTH_DB_PATH", DEFAULT_DB_PATH)
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    return path


def max_request_bytes() -> int:
    raw = os.environ.get("GWSYNTH_MAX_REQUEST_BYTES")
    if not raw:
        return DEFAULT_MAX_REQUEST_BYTES
    try:
        value = int(raw)
    except ValueError:
        return DEFAULT_MAX_REQUEST_BYTES
    return value if value > 0 else DEFAULT_MAX_REQUEST_BYTES


def seed_value() -> int | None:
    raw = os.environ.get("GWSYNTH_SEED")
    if not raw:
        return None
    try:
        return int(raw)
    except ValueError:
        return None
