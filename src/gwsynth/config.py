from __future__ import annotations

import os
from pathlib import Path

DEFAULT_DB_PATH = "./data/gwsynth.db"
DEFAULT_MAX_REQUEST_BYTES = 2_000_000
DEFAULT_RATE_LIMIT_ENABLED = True
DEFAULT_RATE_LIMIT_RPM = 600
DEFAULT_RATE_LIMIT_BURST = 60


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


def rate_limit_enabled() -> bool:
    raw = os.environ.get("GWSYNTH_RATE_LIMIT_ENABLED")
    if raw is None or raw == "":
        return DEFAULT_RATE_LIMIT_ENABLED
    lowered = raw.strip().lower()
    if lowered in {"0", "false", "no", "off"}:
        return False
    if lowered in {"1", "true", "yes", "on"}:
        return True
    return DEFAULT_RATE_LIMIT_ENABLED


def rate_limit_requests_per_minute() -> int:
    raw = os.environ.get("GWSYNTH_RATE_LIMIT_RPM")
    if not raw:
        return DEFAULT_RATE_LIMIT_RPM
    try:
        value = int(raw)
    except ValueError:
        return DEFAULT_RATE_LIMIT_RPM
    return value if value > 0 else DEFAULT_RATE_LIMIT_RPM


def rate_limit_burst() -> int:
    raw = os.environ.get("GWSYNTH_RATE_LIMIT_BURST")
    if not raw:
        return DEFAULT_RATE_LIMIT_BURST
    try:
        value = int(raw)
    except ValueError:
        return DEFAULT_RATE_LIMIT_BURST
    return value if value > 0 else DEFAULT_RATE_LIMIT_BURST


def seed_value() -> int | None:
    raw = os.environ.get("GWSYNTH_SEED")
    if not raw:
        return None
    try:
        return int(raw)
    except ValueError:
        return None
