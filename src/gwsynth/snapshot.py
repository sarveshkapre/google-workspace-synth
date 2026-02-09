from __future__ import annotations

import argparse
import json
import sqlite3
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

from . import __version__
from .db import get_connection, init_db

CURRENT_SNAPSHOT_VERSION = 2
SUPPORTED_SNAPSHOT_VERSIONS = {1, CURRENT_SNAPSHOT_VERSION}

_EXPORT_TABLES: tuple[str, ...] = (
    "users",
    "groups",
    "group_members",
    "items",
    "permissions",
    "share_links",
    "comments",
    "activities",
)

_IMPORT_DELETE_ORDER: tuple[str, ...] = (
    "activities",
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
    "activities",
)


def _now() -> str:
    return datetime.now(UTC).isoformat()

def _parse_tables(value: str | None) -> list[str] | None:
    if value is None:
        return None
    raw = value.strip()
    if not raw:
        return None
    parts = [part.strip() for part in raw.split(",") if part.strip()]
    if not parts:
        return None
    unknown = [part for part in parts if part not in _EXPORT_TABLES]
    if unknown:
        raise ValueError(f"Unknown tables: {', '.join(unknown)}")
    return _normalize_tables(parts)


def _normalize_tables(tables: Iterable[str] | None) -> list[str]:
    if tables is None:
        return list(_EXPORT_TABLES)
    seen: set[str] = set()
    for table in tables:
        name = table.strip()
        if not name:
            continue
        if name not in _EXPORT_TABLES:
            raise ValueError(f"Unknown table: {name}")
        seen.add(name)
    if not seen:
        return list(_EXPORT_TABLES)
    return [table for table in _EXPORT_TABLES if table in seen]


def _table_columns(conn: sqlite3.Connection, table: str) -> list[str]:
    rows = conn.execute(f"PRAGMA table_info({table})").fetchall()
    cols = [row[1] for row in rows]
    if not cols:
        raise ValueError(f"Unknown table: {table}")
    return cols


def _select_all(conn: sqlite3.Connection, table: str) -> list[dict[str, Any]]:
    rows = conn.execute(f"SELECT * FROM {table} ORDER BY rowid").fetchall()
    return [dict(row) for row in rows]

def _schema_columns(conn: sqlite3.Connection, tables: Sequence[str]) -> dict[str, list[str]]:
    return {table: _table_columns(conn, table) for table in tables}

def export_snapshot(
    conn: sqlite3.Connection, *, tables: Iterable[str] | None = None
) -> dict[str, Any]:
    selected = _normalize_tables(tables)
    return {
        "snapshot_version": CURRENT_SNAPSHOT_VERSION,
        "app_version": __version__,
        "exported_at": _now(),
        "exported_tables": selected,
        "schema": _schema_columns(conn, selected),
        "tables": {table: _select_all(conn, table) for table in selected},
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

class _Col:
    def __init__(self, name: str, *, notnull: bool, default: Any) -> None:
        self.name = name
        self.notnull = notnull
        self.default = default


def _table_info(conn: sqlite3.Connection, table: str) -> list[_Col]:
    rows = conn.execute(f"PRAGMA table_info({table})").fetchall()
    if not rows:
        raise ValueError(f"Unknown table: {table}")
    cols: list[_Col] = []
    for row in rows:
        cols.append(_Col(str(row[1]), notnull=bool(row[3]), default=row[4]))
    return cols


def _default_value(col: _Col) -> str | None:
    if col.default is None:
        return None
    # SQLite returns the raw default SQL expression. Our schema does not currently
    # use defaults, but keep this behavior predictable.
    return str(col.default)


def _iter_row_values(
    table: str, cols: list[_Col], rows: Iterable[Any]
) -> Iterable[tuple[Any, ...]]:
    col_names = {col.name for col in cols}
    for idx, raw_row in enumerate(rows):
        if not isinstance(raw_row, dict):
            raise ValueError(f"{table}[{idx}] must be an object")
        row = raw_row
        unknown = [key for key in row.keys() if key not in col_names]
        if unknown:
            raise ValueError(f"{table}[{idx}] has unknown columns: {', '.join(sorted(unknown))}")
        values: list[Any] = []
        for col in cols:
            if col.name in row:
                values.append(
                    _require_str_or_none(row.get(col.name), f"{table}[{idx}].{col.name}")
                )
                continue
            if col.notnull and col.default is None:
                raise ValueError(f"{table}[{idx}] missing required column: {col.name}")
            values.append(_default_value(col))
        yield tuple(values)

def _selected_tables_from_snapshot(snapshot: Mapping[str, Any]) -> list[str]:
    raw_tables = snapshot.get("tables", {})
    if isinstance(raw_tables, dict):
        keys = [str(k) for k in raw_tables.keys()]
        candidate = [k for k in keys if k in _EXPORT_TABLES]
        if candidate:
            return _normalize_tables(candidate)
    exported_tables = snapshot.get("exported_tables")
    if isinstance(exported_tables, list) and all(isinstance(x, str) for x in exported_tables):
        return _normalize_tables(exported_tables)
    return list(_EXPORT_TABLES)


def import_snapshot(
    conn: sqlite3.Connection,
    snapshot: Mapping[str, Any],
    *,
    mode: str = "replace",
    tables: Iterable[str] | None = None,
) -> dict[str, int]:
    if mode not in {"replace", "replace_tables"}:
        raise ValueError("mode must be replace or replace_tables")

    snapshot_version = snapshot.get("snapshot_version")
    if snapshot_version not in SUPPORTED_SNAPSHOT_VERSIONS:
        supported = ", ".join(str(v) for v in sorted(SUPPORTED_SNAPSHOT_VERSIONS))
        raise ValueError(
            f"snapshot_version must be one of: {supported}"
        )

    table_payload = _require_dict(snapshot.get("tables"), "tables")
    selected = _normalize_tables(tables or _selected_tables_from_snapshot(snapshot))

    if mode == "replace" and selected != list(_EXPORT_TABLES):
        raise ValueError("mode=replace requires a full snapshot (all tables)")

    # Schema metadata is optional (v1 snapshots won't have it).
    raw_schema = snapshot.get("schema")
    if raw_schema is not None:
        schema = _require_dict(raw_schema, "schema")
        for table in selected:
            cols = schema.get(table)
            if cols is None:
                continue
            if not isinstance(cols, list) or not all(isinstance(c, str) for c in cols):
                raise ValueError(f"schema.{table} must be a list of strings")
            current_cols = set(_table_columns(conn, table))
            missing = [c for c in cols if c not in current_cols]
            if missing:
                joined = ", ".join(missing)
                raise ValueError(
                    f"Snapshot schema references missing columns for {table}: {joined}"
                )

    conn.execute("PRAGMA foreign_keys = ON")

    delete_order = [t for t in _IMPORT_DELETE_ORDER if t in selected]
    insert_order = [t for t in _IMPORT_INSERT_ORDER if t in selected]

    for table in delete_order:
        conn.execute(f"DELETE FROM {table}")

    inserted: dict[str, int] = {}
    for table in insert_order:
        raw_rows = _require_list(table_payload.get(table, []), f"tables.{table}")
        if not raw_rows:
            inserted[table] = 0
            continue

        cols = _table_info(conn, table)
        placeholders = ", ".join(["?"] * len(cols))
        col_list = ", ".join([col.name for col in cols])
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
    export_p.add_argument(
        "--tables",
        default="",
        help=(
            "Comma-separated subset of tables to export "
            f"(default: all: {', '.join(_EXPORT_TABLES)})"
        ),
    )

    import_p = sub.add_parser("import", help="Import DB snapshot from JSON")
    import_p.add_argument(
        "--in", dest="input", type=Path, default=None, help="Read from file (default: stdin)"
    )
    import_p.add_argument("--mode", choices=["replace", "replace_tables"], default="replace")
    import_p.add_argument(
        "--tables",
        default="",
        help="Comma-separated subset of tables to import (default: inferred from snapshot or all)",
    )

    args = parser.parse_args()
    init_db()

    if args.cmd == "export":
        selected = _parse_tables(args.tables)
        with get_connection() as conn:
            _write_json(export_snapshot(conn, tables=selected), args.out)
        return

    payload = _read_json(args.input)
    snapshot_dict = _require_dict(payload, "snapshot")
    with get_connection() as conn:
        selected = _parse_tables(args.tables)
        import_snapshot(conn, snapshot_dict, mode=args.mode, tables=selected)


if __name__ == "__main__":
    main()
