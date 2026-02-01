from __future__ import annotations

import argparse
import json
import sqlite3
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Iterable, Mapping

from .db import get_connection, init_db

SNAPSHOT_VERSION = 1

_EXPORT_TABLES: tuple[str, ...] = (
    "users",
    "groups",
    "group_members",
    "items",
    "permissions",
    "share_links",
    "comments",
)

_IMPORT_DELETE_ORDER: tuple[str, ...] = (
    "comments",
    "share_links",
    "permissions",
    "group_members",
    "items",
    "groups",
    "users",
)

_IMPORT_INSERT_ORDER: tuple[str, ...] = (
    "users",
    "groups",
    "items",
    "group_members",
    "permissions",
    "share_links",
    "comments",
)


def _now() -> str:
    return datetime.now(UTC).isoformat()


def _table_columns(conn: sqlite3.Connection, table: str) -> list[str]:
    rows = conn.execute(f"PRAGMA table_info({table})").fetchall()
    cols = [row[1] for row in rows]
    if not cols:
        raise ValueError(f"Unknown table: {table}")
    return cols


def _select_all(conn: sqlite3.Connection, table: str) -> list[dict[str, Any]]:
    rows = conn.execute(f"SELECT * FROM {table} ORDER BY rowid").fetchall()
    return [dict(row) for row in rows]


def export_snapshot(conn: sqlite3.Connection) -> dict[str, Any]:
    return {
        "snapshot_version": SNAPSHOT_VERSION,
        "exported_at": _now(),
        "tables": {table: _select_all(conn, table) for table in _EXPORT_TABLES},
    }


def _require_dict(value: Any, label: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ValueError(f"{label} must be an object")
    return value


def _require_list(value: Any, label: str) -> list[Any]:
    if not isinstance(value, list):
        raise ValueError(f"{label} must be a list")
    return value


def _require_str_or_none(value: Any, label: str) -> str | None:
    if value is None:
        return None
    if isinstance(value, str):
        return value
    raise ValueError(f"{label} must be a string or null")


def _iter_row_values(table: str, cols: list[str], rows: Iterable[Any]) -> Iterable[tuple[Any, ...]]:
    for idx, raw_row in enumerate(rows):
        if not isinstance(raw_row, dict):
            raise ValueError(f"{table}[{idx}] must be an object")
        row = raw_row
        missing = [c for c in cols if c not in row]
        if missing:
            raise ValueError(f"{table}[{idx}] missing columns: {', '.join(missing)}")
        values: list[Any] = []
        for col in cols:
            values.append(_require_str_or_none(row.get(col), f"{table}[{idx}].{col}"))
        yield tuple(values)


def import_snapshot(
    conn: sqlite3.Connection,
    snapshot: Mapping[str, Any],
    *,
    mode: str = "replace",
) -> dict[str, int]:
    if mode != "replace":
        raise ValueError("mode must be replace")

    snapshot_version = snapshot.get("snapshot_version")
    if snapshot_version != SNAPSHOT_VERSION:
        raise ValueError(f"snapshot_version must be {SNAPSHOT_VERSION}")

    tables = _require_dict(snapshot.get("tables"), "tables")

    conn.execute("PRAGMA foreign_keys = OFF")

    for table in _IMPORT_DELETE_ORDER:
        conn.execute(f"DELETE FROM {table}")

    inserted: dict[str, int] = {}
    for table in _IMPORT_INSERT_ORDER:
        raw_rows = _require_list(tables.get(table, []), f"tables.{table}")
        if not raw_rows:
            inserted[table] = 0
            continue

        cols = _table_columns(conn, table)
        placeholders = ", ".join(["?"] * len(cols))
        col_list = ", ".join(cols)
        conn.executemany(
            f"INSERT INTO {table} ({col_list}) VALUES ({placeholders})",
            list(_iter_row_values(table, cols, raw_rows)),
        )
        inserted[table] = len(raw_rows)

    violations = conn.execute("PRAGMA foreign_key_check").fetchall()
    if violations:
        raise ValueError(f"Snapshot violates foreign keys ({len(violations)} violations)")

    return inserted


def _read_json(path: Path | None) -> Any:
    if path is None:
        return json.load(sys.stdin)
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(payload: Any, path: Path | None) -> None:
    text = json.dumps(payload, indent=2, sort_keys=True) + "\n"
    if path is None:
        sys.stdout.write(text)
        return
    path.write_text(text, encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="Export/import Google Workspace Synth snapshots")
    sub = parser.add_subparsers(dest="cmd", required=True)

    export_p = sub.add_parser("export", help="Export DB snapshot as JSON")
    export_p.add_argument("--out", type=Path, default=None, help="Write to file (default: stdout)")

    import_p = sub.add_parser("import", help="Import DB snapshot from JSON")
    import_p.add_argument(
        "--in", dest="input", type=Path, default=None, help="Read from file (default: stdin)"
    )
    import_p.add_argument("--mode", choices=["replace"], default="replace")

    args = parser.parse_args()
    init_db()

    if args.cmd == "export":
        with get_connection() as conn:
            _write_json(export_snapshot(conn), args.out)
        return

    payload = _read_json(args.input)
    snapshot_dict = _require_dict(payload, "snapshot")
    with get_connection() as conn:
        import_snapshot(conn, snapshot_dict, mode=args.mode)


if __name__ == "__main__":
    main()
