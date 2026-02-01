from __future__ import annotations

import os
from pathlib import Path

DEFAULT_DB_PATH = "./data/gwsynth.db"


def db_path() -> str:
    path = os.environ.get("GWSYNTH_DB_PATH", DEFAULT_DB_PATH)
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    return path


def seed_value() -> int | None:
    raw = os.environ.get("GWSYNTH_SEED")
    if not raw:
        return None
    try:
        return int(raw)
    except ValueError:
        return None
