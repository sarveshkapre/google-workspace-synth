from __future__ import annotations

import gzip
import hashlib
import io
import json
import secrets
import sqlite3
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Callable, Iterable, Iterator, cast
from uuid import uuid4

from flask import Flask, Response, jsonify, request, send_from_directory, stream_with_context

from .config import (
    api_key,
    db_path,
    snapshot_max_decompressed_bytes,
    swagger_ui_cdn_base_url,
    swagger_ui_local_dir,
    swagger_ui_mode,
)
from .db import get_connection
from .openapi import openapi_spec
from .pagination import Cursor, decode_cursor, encode_cursor, parse_limit
from .schemas import ItemType, PrincipalType, RoleType
from .snapshot import export_snapshot, import_snapshot, iter_export_snapshot_json, iter_gzip_bytes

VALID_ITEM_TYPES: set[ItemType] = {"folder", "doc", "sheet"}
VALID_ROLES: set[RoleType] = {"owner", "editor", "viewer"}
VALID_PRINCIPAL_TYPES: set[PrincipalType] = {"user", "group", "anyone"}


def _now() -> str:
    return datetime.now(UTC).isoformat()


def _json_error(message: str, status_code: int) -> tuple[Any, int]:
    return jsonify({"error": message}), status_code


def _require_str(data: dict[str, Any], key: str) -> str:
    value = data.get(key)
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{key} is required")
    return value.strip()


def _optional_str(data: dict[str, Any], key: str) -> str | None:
    value = data.get(key)
    if value is None:
        return None
    if not isinstance(value, str):
        raise ValueError(f"{key} must be a string")
    return value


def _parse_item_type(value: str) -> ItemType:
    if value not in VALID_ITEM_TYPES:
        raise ValueError("item_type must be folder, doc, or sheet")
    return value  # type: ignore[return-value]


def _parse_role(value: str) -> RoleType:
    if value not in VALID_ROLES:
        raise ValueError("role must be owner, editor, or viewer")
    return value  # type: ignore[return-value]


def _parse_principal_type(value: str) -> PrincipalType:
    if value not in VALID_PRINCIPAL_TYPES:
        raise ValueError("principal_type must be user, group, or anyone")
    return value  # type: ignore[return-value]


def _row_to_item(row: sqlite3.Row) -> dict[str, Any]:
    sheet_data = json.loads(row["content_json"]) if row["content_json"] else None
    return {
        "id": row["id"],
        "name": row["name"],
        "item_type": row["item_type"],
        "parent_id": row["parent_id"],
        "owner_user_id": row["owner_user_id"],
        "content_text": row["content_text"],
        "sheet_data": sheet_data,
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
    }


def _row_to_group_member(row: sqlite3.Row) -> dict[str, Any]:
    return {
        "id": row["id"],
        "group_id": row["group_id"],
        "user_id": row["user_id"],
        "email": row["email"],
        "display_name": row["display_name"],
        "created_at": row["created_at"],
    }


def _parse_sheet_data(value: Any, *, required: bool) -> dict[str, str] | None:
    if value is None:
        if required:
            raise ValueError("sheet_data required for sheets")
        return None
    if not isinstance(value, dict):
        raise ValueError("sheet_data must be an object")
    parsed: dict[str, str] = {}
    for cell, cell_value in value.items():
        if not isinstance(cell, str) or not isinstance(cell_value, str):
            raise ValueError("sheet_data must map string cells to string values")
        parsed[cell] = cell_value
    return parsed


def _json_dumps(data: dict[str, Any]) -> str:
    return json.dumps(data, separators=(",", ":"), sort_keys=True)


def _split_header_tokens(value: str) -> list[str]:
    return [part.strip() for part in value.split(",") if part.strip()]


def _snapshot_etag(
    *,
    tables: list[str] | None,
    gzip_enabled: bool,
    stream_enabled: bool,
) -> str:
    """
    Compute an ETag for the snapshot representation without materializing the snapshot.

    This is a best-effort cache key for local/demo usage (based on DB file mtime/size + query
    params).
    """
    p = Path(db_path())
    try:
        st = p.stat()
        size = st.st_size
        mtime_ns = st.st_mtime_ns
    except FileNotFoundError:
        size = 0
        mtime_ns = 0

    tables_key = ",".join(tables or [])
    key = f"{size}:{mtime_ns}:{tables_key}:{int(gzip_enabled)}:{int(stream_enabled)}".encode(
        "utf-8"
    )
    digest = hashlib.sha256(key).hexdigest()[:32]
    return f'W/"{digest}"'


def _if_none_match_matches(etag: str) -> bool:
    raw = request.headers.get("If-None-Match")
    if not raw:
        return False
    tokens = _split_header_tokens(raw)
    return etag in tokens or "*" in tokens


def _gunzip_limited(data: bytes, *, limit: int) -> bytes:
    with gzip.GzipFile(fileobj=io.BytesIO(data)) as f:
        out = f.read(limit + 1)
    if len(out) > limit:
        raise ValueError(f"Decompressed snapshot body exceeds {limit} bytes")
    return out


def _request_json_object() -> dict[str, Any]:
    enc = request.headers.get("Content-Encoding", "")
    encodings = {token.lower() for token in _split_header_tokens(enc)}
    if "gzip" in encodings:
        raw = request.get_data(cache=False)
        try:
            decompressed = _gunzip_limited(raw, limit=snapshot_max_decompressed_bytes())
        except OSError as exc:
            raise ValueError("Invalid gzip request body") from exc
        try:
            payload = json.loads(decompressed.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise ValueError("Invalid JSON body") from exc
    else:
        payload = request.get_json(silent=True)

    if payload is None:
        raise ValueError("JSON body required")
    if not isinstance(payload, dict):
        raise ValueError("Body must be an object")
    return cast(dict[str, Any], payload)


def _record_activity(
    conn: sqlite3.Connection,
    *,
    item_id: str,
    event_type: str,
    actor_user_id: str | None,
    data: dict[str, Any],
) -> None:
    conn.execute(
        """
        INSERT INTO activities (id, item_id, event_type, actor_user_id, data_json, created_at)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (
            str(uuid4()),
            item_id,
            event_type,
            actor_user_id,
            _json_dumps(data),
            _now(),
        ),
    )


def _page_clause_asc(
    created_at_col: str, id_col: str, cursor: Cursor
) -> tuple[str, tuple[str, str, str]]:
    clause = f"({created_at_col} > ? OR ({created_at_col} = ? AND {id_col} > ?))"
    return clause, (cursor.created_at, cursor.created_at, cursor.id)


def _page_clause_desc(
    created_at_col: str, id_col: str, cursor: Cursor
) -> tuple[str, tuple[str, str, str]]:
    clause = f"({created_at_col} < ? OR ({created_at_col} = ? AND {id_col} < ?))"
    return clause, (cursor.created_at, cursor.created_at, cursor.id)


def _paginate_rows_asc(
    conn: sqlite3.Connection,
    *,
    table: str,
    where: list[str],
    params: list[Any],
    limit: int,
    cursor: Cursor | None,
) -> tuple[list[sqlite3.Row], str | None]:
    where_clauses = list(where)
    all_params: list[Any] = list(params)
    if cursor is not None:
        clause, clause_params = _page_clause_asc("created_at", "id", cursor)
        where_clauses.append(clause)
        all_params.extend(list(clause_params))

    where_sql = f" WHERE {' AND '.join(where_clauses)}" if where_clauses else ""
    rows = conn.execute(
        f"SELECT * FROM {table}{where_sql} ORDER BY created_at, id LIMIT ?",
        (*all_params, limit + 1),
    ).fetchall()

    next_cursor = None
    if len(rows) > limit:
        last = rows[limit - 1]
        next_cursor = encode_cursor(Cursor(created_at=last["created_at"], id=last["id"]))
        rows = rows[:limit]
    return rows, next_cursor


def _paginate_rows_desc(
    conn: sqlite3.Connection,
    *,
    table: str,
    where: list[str],
    params: list[Any],
    limit: int,
    cursor: Cursor | None,
) -> tuple[list[sqlite3.Row], str | None]:
    where_clauses = list(where)
    all_params: list[Any] = list(params)
    if cursor is not None:
        clause, clause_params = _page_clause_desc("created_at", "id", cursor)
        where_clauses.append(clause)
        all_params.extend(list(clause_params))

    where_sql = f" WHERE {' AND '.join(where_clauses)}" if where_clauses else ""
    rows = conn.execute(
        f"SELECT * FROM {table}{where_sql} ORDER BY created_at DESC, id DESC LIMIT ?",
        (*all_params, limit + 1),
    ).fetchall()

    next_cursor = None
    if len(rows) > limit:
        last = rows[limit - 1]
        next_cursor = encode_cursor(Cursor(created_at=last["created_at"], id=last["id"]))
        rows = rows[:limit]
    return rows, next_cursor


def _paginate_group_members_with_users(
    conn: sqlite3.Connection,
    *,
    group_id: str,
    limit: int,
    cursor: Cursor | None,
) -> tuple[list[sqlite3.Row], str | None]:
    where_clauses = ["gm.group_id = ?"]
    all_params: list[Any] = [group_id]
    if cursor is not None:
        clause, clause_params = _page_clause_asc("gm.created_at", "gm.id", cursor)
        where_clauses.append(clause)
        all_params.extend(list(clause_params))

    where_sql = f"WHERE {' AND '.join(where_clauses)}" if where_clauses else ""
    rows = conn.execute(
        f"""
        SELECT
            gm.id,
            gm.group_id,
            gm.user_id,
            gm.created_at,
            u.email,
            u.display_name
        FROM group_members gm
        JOIN users u ON u.id = gm.user_id
        {where_sql}
        ORDER BY gm.created_at, gm.id
        LIMIT ?
        """,
        (*all_params, limit + 1),
    ).fetchall()

    next_cursor = None
    if len(rows) > limit:
        last = rows[limit - 1]
        next_cursor = encode_cursor(Cursor(created_at=last["created_at"], id=last["id"]))
        rows = rows[:limit]
    return rows, next_cursor


def register_routes(app: Flask) -> None:
    def handler(fn: Callable[..., Any]) -> Callable[..., Any]:
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            try:
                return fn(*args, **kwargs)
            except ValueError as exc:
                return _json_error(str(exc), 400)

        wrapper.__name__ = fn.__name__
        return wrapper

    def swagger_ui_asset_urls() -> tuple[str, str] | None:
        mode = swagger_ui_mode()
        local_dir = Path(swagger_ui_local_dir())
        local_css = local_dir / "swagger-ui.css"
        local_js = local_dir / "swagger-ui-bundle.js"
        local_available = local_css.is_file() and local_js.is_file()

        if mode == "local":
            if local_available:
                return ("/docs-assets/swagger-ui.css", "/docs-assets/swagger-ui-bundle.js")
            return None
        if mode == "auto" and local_available:
            return ("/docs-assets/swagger-ui.css", "/docs-assets/swagger-ui-bundle.js")

        cdn_base = swagger_ui_cdn_base_url()
        return (f"{cdn_base}/swagger-ui.css", f"{cdn_base}/swagger-ui-bundle.js")

    @app.get("/health")
    def health() -> Any:
        return jsonify({"status": "ok"})

    @app.get("/")
    def index() -> Any:
        auth_enabled = api_key() is not None
        auth_line = (
            "API key auth: enabled (most API routes require X-API-Key or Authorization: Bearer)"
            if auth_enabled
            else "API key auth: disabled (local-dev default)"
        )
        html = f"""
<!doctype html>
<html lang="en">
  <head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <title>GWSynth</title>
    <style>
      :root {{ color-scheme: light; }}
      body {{
        font-family: ui-sans-serif, system-ui, -apple-system, Segoe UI, sans-serif;
        margin: 32px;
      }}
      code {{ background: #f5f5f5; padding: 2px 6px; border-radius: 6px; }}
      .links a {{ display: inline-block; margin-right: 14px; }}
      .muted {{ color: #555; }}
      pre {{ background: #f5f5f5; padding: 12px; border-radius: 10px; overflow-x: auto; }}
    </style>
  </head>
  <body>
    <h1>Google Workspace Synth</h1>
    <p class="muted">{auth_line}</p>
    <p class="links">
      <a href="/docs">API docs</a>
      <a href="/openapi.json">OpenAPI</a>
      <a href="/health">Health</a>
      <a href="/stats">Stats</a>
    </p>

    <h2>Common Env Vars</h2>
    <ul>
      <li><code>GWSYNTH_DB_PATH</code></li>
      <li><code>GWSYNTH_API_KEY</code></li>
      <li><code>GWSYNTH_MAX_REQUEST_BYTES</code></li>
      <li>
        <code>GWSYNTH_RATE_LIMIT_ENABLED</code>, <code>GWSYNTH_RATE_LIMIT_RPM</code>,
        <code>GWSYNTH_RATE_LIMIT_BURST</code>
      </li>
      <li><code>GWSYNTH_TRUST_PROXY</code></li>
    </ul>

    <h2>Quick Curl</h2>
    <pre><code>curl -s http://localhost:8000/health
curl -s http://localhost:8000/users
curl -s http://localhost:8000/snapshot &gt; snapshot.json</code></pre>
  </body>
</html>
"""
        return Response(html, mimetype="text/html")

    @app.get("/openapi.json")
    def openapi() -> Any:
        return jsonify(openapi_spec())

    @app.get("/docs-assets/<path:asset_name>")
    def docs_asset(asset_name: str) -> Any:
        allowed = {"swagger-ui.css", "swagger-ui-bundle.js"}
        if asset_name not in allowed:
            return _json_error("Asset not found", 404)

        local_dir = Path(swagger_ui_local_dir())
        asset_path = local_dir / asset_name
        if not asset_path.is_file():
            return _json_error("Asset not found", 404)
        return send_from_directory(local_dir, asset_name)

    @app.get("/docs")
    def docs() -> Any:
        asset_urls = swagger_ui_asset_urls()
        if asset_urls is None:
            local_dir = swagger_ui_local_dir()
            html = f"""
<!doctype html>
<html lang="en">
  <head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <title>GWSynth API Docs</title>
    <style>
      body {{ font-family: ui-sans-serif, system-ui, sans-serif; margin: 24px; }}
      code {{ background: #f5f5f5; padding: 2px 6px; border-radius: 6px; }}
    </style>
  </head>
  <body>
    <h1>Swagger UI assets not found</h1>
    <p>
      <code>GWSYNTH_SWAGGER_UI_MODE=local</code> requires vendored assets in
      <code>{local_dir}</code>.
    </p>
    <p>
      Fetch assets with:
      <code>PYTHONPATH=src ./.venv/bin/python scripts/vendor_swagger_ui.py --out {local_dir}</code>
    </p>
  </body>
</html>
"""
            return Response(html, status=503, mimetype="text/html")

        css_url, js_url = asset_urls
        html = f"""
<!doctype html>
<html lang="en">
  <head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <title>GWSynth API Docs</title>
    <link rel="stylesheet" href="{css_url}" />
    <style>
      body {{ margin: 0; }}
    </style>
  </head>
  <body>
    <div id="swagger-ui"></div>
    <script src="{js_url}"></script>
    <script>
      window.onload = () => {{
        SwaggerUIBundle({{
          url: "/openapi.json",
          dom_id: "#swagger-ui",
          persistAuthorization: true,
        }});
      }};
    </script>
  </body>
</html>
"""
        return Response(html, mimetype="text/html")

    @app.get("/stats")
    def stats() -> Any:
        with get_connection() as conn:
            users = conn.execute("SELECT COUNT(*) FROM users").fetchone()[0]
            groups = conn.execute("SELECT COUNT(*) FROM groups").fetchone()[0]
            items = conn.execute("SELECT COUNT(*) FROM items").fetchone()[0]
            permissions = conn.execute("SELECT COUNT(*) FROM permissions").fetchone()[0]
            share_links = conn.execute("SELECT COUNT(*) FROM share_links").fetchone()[0]
            comments = conn.execute("SELECT COUNT(*) FROM comments").fetchone()[0]
            activities = conn.execute("SELECT COUNT(*) FROM activities").fetchone()[0]
        return jsonify(
            {
                "users": users,
                "groups": groups,
                "items": items,
                "permissions": permissions,
                "share_links": share_links,
                "comments": comments,
                "activities": activities,
            }
        )

    @app.get("/snapshot")
    def get_snapshot() -> Any:
        tables_param = request.args.get("tables")
        gzip_param = request.args.get("gzip", "")
        stream_param = request.args.get("stream", "")

        tables = None
        if tables_param is not None and tables_param.strip():
            tables = [t.strip() for t in tables_param.split(",") if t.strip()]

        gzip_enabled = gzip_param.strip().lower() in {"1", "true", "yes", "on"}
        stream_enabled = stream_param.strip().lower() in {"1", "true", "yes", "on"}

        etag = _snapshot_etag(
            tables=tables,
            gzip_enabled=gzip_enabled,
            stream_enabled=stream_enabled,
        )
        base_headers = {"ETag": etag, "Cache-Control": "no-cache"}
        if _if_none_match_matches(etag):
            return Response(status=304, headers=base_headers)

        if gzip_enabled or stream_enabled:

            def generate() -> Iterator[bytes]:
                with get_connection() as conn:
                    chunks: Iterable[bytes] = iter_export_snapshot_json(conn, tables=tables)
                    if gzip_enabled:
                        chunks = iter_gzip_bytes(chunks)
                    yield from chunks

            headers = dict(base_headers)
            if gzip_enabled:
                headers["Content-Encoding"] = "gzip"
            return Response(
                stream_with_context(cast(Any, generate())),
                mimetype="application/json",
                headers=headers,
            )

        with get_connection() as conn:
            resp = jsonify(export_snapshot(conn, tables=tables))
            resp.headers.update(base_headers)
            return resp

    @app.post("/snapshot")
    @handler
    def post_snapshot() -> Any:
        mode = request.args.get("mode", "replace")
        tables_param = request.args.get("tables")
        tables = None
        if tables_param is not None and tables_param.strip():
            tables = [t.strip() for t in tables_param.split(",") if t.strip()]
        payload = _request_json_object()

        with get_connection() as conn:
            inserted = import_snapshot(conn, payload, mode=mode, tables=tables)
            return jsonify({"status": "imported", "inserted": inserted})

    @app.post("/users")
    @handler
    def create_user() -> Any:
        payload = request.get_json(silent=True) or {}
        email = _require_str(payload, "email")
        display_name = _require_str(payload, "display_name")
        with get_connection() as conn:
            existing = conn.execute("SELECT id FROM users WHERE email = ?", (email,)).fetchone()
            if existing:
                return _json_error("Email already exists", 409)
            user_id = str(uuid4())
            created_at = _now()
            conn.execute(
                "INSERT INTO users (id, email, display_name, created_at) VALUES (?, ?, ?, ?)",
                (user_id, email, display_name, created_at),
            )
        return jsonify(
            {
                "id": user_id,
                "email": email,
                "display_name": display_name,
                "created_at": created_at,
            }
        ), 201

    @app.get("/users")
    @handler
    def list_users() -> Any:
        limit = parse_limit(request.args.get("limit"))
        cursor_raw = request.args.get("cursor")
        cursor = decode_cursor(cursor_raw) if cursor_raw else None
        with get_connection() as conn:
            if limit is None:
                rows = conn.execute("SELECT * FROM users ORDER BY created_at, id").fetchall()
                return jsonify(
                    [
                        {
                            "id": row["id"],
                            "email": row["email"],
                            "display_name": row["display_name"],
                            "created_at": row["created_at"],
                        }
                        for row in rows
                    ]
                )
            rows, next_cursor = _paginate_rows_asc(
                conn, table="users", where=[], params=[], limit=limit, cursor=cursor
            )
            return jsonify(
                {
                    "users": [
                        {
                            "id": row["id"],
                            "email": row["email"],
                            "display_name": row["display_name"],
                            "created_at": row["created_at"],
                        }
                        for row in rows
                    ],
                    "next_cursor": next_cursor,
                }
            )

    @app.get("/users/<user_id>")
    def get_user(user_id: str) -> Any:
        with get_connection() as conn:
            row = conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
            if not row:
                return _json_error("User not found", 404)
            return jsonify(
                {
                    "id": row["id"],
                    "email": row["email"],
                    "display_name": row["display_name"],
                    "created_at": row["created_at"],
                }
            )

    @app.post("/groups")
    @handler
    def create_group() -> Any:
        payload = request.get_json(silent=True) or {}
        name = _require_str(payload, "name")
        description = _optional_str(payload, "description") or ""
        with get_connection() as conn:
            group_id = str(uuid4())
            created_at = _now()
            conn.execute(
                "INSERT INTO groups (id, name, description, created_at) VALUES (?, ?, ?, ?)",
                (group_id, name, description, created_at),
            )
        return jsonify(
            {
                "id": group_id,
                "name": name,
                "description": description,
                "created_at": created_at,
            }
        ), 201

    @app.get("/groups")
    @handler
    def list_groups() -> Any:
        limit = parse_limit(request.args.get("limit"))
        cursor_raw = request.args.get("cursor")
        cursor = decode_cursor(cursor_raw) if cursor_raw else None
        with get_connection() as conn:
            if limit is None:
                rows = conn.execute("SELECT * FROM groups ORDER BY created_at, id").fetchall()
                return jsonify(
                    [
                        {
                            "id": row["id"],
                            "name": row["name"],
                            "description": row["description"],
                            "created_at": row["created_at"],
                        }
                        for row in rows
                    ]
                )
            rows, next_cursor = _paginate_rows_asc(
                conn, table="groups", where=[], params=[], limit=limit, cursor=cursor
            )
            return jsonify(
                {
                    "groups": [
                        {
                            "id": row["id"],
                            "name": row["name"],
                            "description": row["description"],
                            "created_at": row["created_at"],
                        }
                        for row in rows
                    ],
                    "next_cursor": next_cursor,
                }
            )

    @app.get("/groups/<group_id>")
    def get_group(group_id: str) -> Any:
        with get_connection() as conn:
            row = conn.execute("SELECT * FROM groups WHERE id = ?", (group_id,)).fetchone()
            if not row:
                return _json_error("Group not found", 404)
            return jsonify(
                {
                    "id": row["id"],
                    "name": row["name"],
                    "description": row["description"],
                    "created_at": row["created_at"],
                }
            )

    @app.post("/groups/<group_id>/members")
    @handler
    def add_group_member(group_id: str) -> Any:
        payload = request.get_json(silent=True) or {}
        user_id = _require_str(payload, "user_id")
        with get_connection() as conn:
            group = conn.execute("SELECT * FROM groups WHERE id = ?", (group_id,)).fetchone()
            if not group:
                return _json_error("Group not found", 404)
            user = conn.execute("SELECT id FROM users WHERE id = ?", (user_id,)).fetchone()
            if not user:
                return _json_error("User not found", 404)
            try:
                conn.execute(
                    "INSERT INTO group_members (id, group_id, user_id, created_at) "
                    "VALUES (?, ?, ?, ?)",
                    (str(uuid4()), group_id, user_id, _now()),
                )
            except sqlite3.IntegrityError:
                pass
            return jsonify(
                {
                    "id": group["id"],
                    "name": group["name"],
                    "description": group["description"],
                    "created_at": group["created_at"],
                }
            ), 201

    @app.get("/groups/<group_id>/members")
    @handler
    def list_group_members(group_id: str) -> Any:
        limit = parse_limit(request.args.get("limit"))
        cursor_raw = request.args.get("cursor")
        cursor = decode_cursor(cursor_raw) if cursor_raw else None
        with get_connection() as conn:
            group = conn.execute("SELECT id FROM groups WHERE id = ?", (group_id,)).fetchone()
            if not group:
                return _json_error("Group not found", 404)

            if limit is None:
                rows = conn.execute(
                    """
                    SELECT
                        gm.id,
                        gm.group_id,
                        gm.user_id,
                        gm.created_at,
                        u.email,
                        u.display_name
                    FROM group_members gm
                    JOIN users u ON u.id = gm.user_id
                    WHERE gm.group_id = ?
                    ORDER BY gm.created_at, gm.id
                    """,
                    (group_id,),
                ).fetchall()
                return jsonify(
                    {
                        "members": [_row_to_group_member(row) for row in rows]
                    }
                )

            rows, next_cursor = _paginate_group_members_with_users(
                conn,
                group_id=group_id,
                limit=limit,
                cursor=cursor,
            )
            return jsonify(
                {"members": [_row_to_group_member(row) for row in rows], "next_cursor": next_cursor}
            )

    @app.delete("/groups/<group_id>/members/<user_id>")
    def remove_group_member(group_id: str, user_id: str) -> Any:
        with get_connection() as conn:
            group = conn.execute("SELECT * FROM groups WHERE id = ?", (group_id,)).fetchone()
            if not group:
                return _json_error("Group not found", 404)
            conn.execute(
                "DELETE FROM group_members WHERE group_id = ? AND user_id = ?", (group_id, user_id)
            )
            return jsonify(
                {
                    "id": group["id"],
                    "name": group["name"],
                    "description": group["description"],
                    "created_at": group["created_at"],
                }
            )

    @app.post("/items")
    @handler
    def create_item() -> Any:
        payload = request.get_json(silent=True) or {}
        name = _require_str(payload, "name")
        item_type = _parse_item_type(_require_str(payload, "item_type"))
        parent_id = _optional_str(payload, "parent_id")
        owner_user_id = _optional_str(payload, "owner_user_id")
        content_text = _optional_str(payload, "content_text")
        sheet_data = _parse_sheet_data(payload.get("sheet_data"), required=False)

        content_json = None
        if item_type == "doc":
            if sheet_data is not None:
                raise ValueError("sheet_data is only allowed for sheets")
            content_text = content_text or ""
        elif item_type == "sheet":
            if content_text is not None:
                raise ValueError("content_text is only allowed for docs")
            content_text = None
            content_json = json.dumps(sheet_data or {})
        else:
            if content_text is not None:
                raise ValueError("content_text is only allowed for docs")
            if sheet_data is not None:
                raise ValueError("sheet_data is only allowed for sheets")
            content_text = None

        with get_connection() as conn:
            if parent_id:
                parent = conn.execute(
                    "SELECT item_type FROM items WHERE id = ?",
                    (parent_id,),
                ).fetchone()
                if not parent:
                    return _json_error("Parent not found", 404)
                if parent["item_type"] != "folder":
                    return _json_error("Parent must be a folder", 400)
            if owner_user_id:
                owner = conn.execute(
                    "SELECT id FROM users WHERE id = ?",
                    (owner_user_id,),
                ).fetchone()
                if not owner:
                    return _json_error("Owner not found", 404)

            item_id = str(uuid4())
            created_at = _now()
            conn.execute(
                """
                INSERT INTO items (
                    id,
                    name,
                    item_type,
                    parent_id,
                    owner_user_id,
                    content_text,
                    content_json,
                    created_at,
                    updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    item_id,
                    name,
                    item_type,
                    parent_id,
                    owner_user_id,
                    content_text,
                    content_json,
                    created_at,
                    created_at,
                ),
            )
            _record_activity(
                conn,
                item_id=item_id,
                event_type="item.created",
                actor_user_id=owner_user_id,
                data={"item_type": item_type, "name": name, "parent_id": parent_id},
            )
            row = conn.execute("SELECT * FROM items WHERE id = ?", (item_id,)).fetchone()
        return jsonify(_row_to_item(row)), 201

    @app.get("/items")
    @handler
    def list_items() -> Any:
        parent_id = request.args.get("parent_id")
        owner_user_id = request.args.get("owner_user_id")
        owner_user_id = owner_user_id.strip() if owner_user_id else None
        item_type_raw = request.args.get("item_type")
        item_type = _parse_item_type(item_type_raw.strip()) if item_type_raw else None
        limit = parse_limit(request.args.get("limit"))
        cursor_raw = request.args.get("cursor")
        cursor = decode_cursor(cursor_raw) if cursor_raw else None
        with get_connection() as conn:
            where: list[str] = []
            params: list[Any] = []
            if parent_id is not None:
                where.append("parent_id = ?")
                params.append(parent_id)
            if owner_user_id is not None:
                if not owner_user_id:
                    return _json_error("owner_user_id must be non-empty", 400)
                where.append("owner_user_id = ?")
                params.append(owner_user_id)
            if item_type is not None:
                where.append("item_type = ?")
                params.append(item_type)

            if limit is None:
                where_sql = f" WHERE {' AND '.join(where)}" if where else ""
                rows = conn.execute(
                    f"SELECT * FROM items{where_sql} ORDER BY created_at, id",
                    tuple(params),
                ).fetchall()
                return jsonify({"items": [_row_to_item(row) for row in rows]})

            rows, next_cursor = _paginate_rows_asc(
                conn, table="items", where=where, params=params, limit=limit, cursor=cursor
            )
            return jsonify(
                {"items": [_row_to_item(row) for row in rows], "next_cursor": next_cursor}
            )

    @app.get("/items/<item_id>")
    def get_item(item_id: str) -> Any:
        with get_connection() as conn:
            row = conn.execute("SELECT * FROM items WHERE id = ?", (item_id,)).fetchone()
            if not row:
                return _json_error("Item not found", 404)
        return jsonify(_row_to_item(row))

    @app.put("/items/<item_id>/content")
    @handler
    def update_item_content(item_id: str) -> Any:
        payload = request.get_json(silent=True) or {}
        actor_user_id = _optional_str(payload, "actor_user_id")
        with get_connection() as conn:
            row = conn.execute("SELECT * FROM items WHERE id = ?", (item_id,)).fetchone()
            if not row:
                return _json_error("Item not found", 404)
            if actor_user_id:
                actor = conn.execute(
                    "SELECT id FROM users WHERE id = ?",
                    (actor_user_id,),
                ).fetchone()
                if not actor:
                    return _json_error("Actor not found", 404)
            if row["item_type"] == "doc":
                content_text = _optional_str(payload, "content_text")
                if content_text is None:
                    raise ValueError("content_text required for docs")
                conn.execute(
                    "UPDATE items SET content_text = ?, updated_at = ? WHERE id = ?",
                    (content_text, _now(), item_id),
                )
                _record_activity(
                    conn,
                    item_id=item_id,
                    event_type="item.content_updated",
                    actor_user_id=actor_user_id,
                    data={"content_text_length": len(content_text)},
                )
            elif row["item_type"] == "sheet":
                sheet_data = _parse_sheet_data(payload.get("sheet_data"), required=True)
                assert sheet_data is not None
                conn.execute(
                    "UPDATE items SET content_json = ?, updated_at = ? WHERE id = ?",
                    (json.dumps(sheet_data), _now(), item_id),
                )
                _record_activity(
                    conn,
                    item_id=item_id,
                    event_type="item.content_updated",
                    actor_user_id=actor_user_id,
                    data={"sheet_cell_count": len(sheet_data)},
                )
            else:
                return _json_error("Folders have no content", 400)
            row = conn.execute("SELECT * FROM items WHERE id = ?", (item_id,)).fetchone()
        return jsonify(_row_to_item(row))

    @app.post("/items/<item_id>/permissions")
    @handler
    def create_permission(item_id: str) -> Any:
        payload = request.get_json(silent=True) or {}
        actor_user_id = _optional_str(payload, "actor_user_id")
        principal_type = _parse_principal_type(_require_str(payload, "principal_type"))
        principal_id = _optional_str(payload, "principal_id")
        principal_id = principal_id.strip() if principal_id is not None else None
        role = _parse_role(_require_str(payload, "role"))

        with get_connection() as conn:
            item = conn.execute("SELECT id FROM items WHERE id = ?", (item_id,)).fetchone()
            if not item:
                return _json_error("Item not found", 404)
            if actor_user_id:
                actor = conn.execute(
                    "SELECT id FROM users WHERE id = ?",
                    (actor_user_id,),
                ).fetchone()
                if not actor:
                    return _json_error("Actor not found", 404)
            if principal_type == "anyone":
                if principal_id is not None:
                    raise ValueError("principal_id must be omitted for anyone")
                principal_id = None
            elif not principal_id:
                raise ValueError("principal_id required")
            elif principal_type == "user":
                user = conn.execute(
                    "SELECT id FROM users WHERE id = ?",
                    (principal_id,),
                ).fetchone()
                if not user:
                    return _json_error("User not found", 404)
            elif principal_type == "group":
                group = conn.execute(
                    "SELECT id FROM groups WHERE id = ?",
                    (principal_id,),
                ).fetchone()
                if not group:
                    return _json_error("Group not found", 404)

            perm_id = str(uuid4())
            created_at = _now()
            conn.execute(
                """
                INSERT INTO permissions (
                    id,
                    item_id,
                    principal_type,
                    principal_id,
                    role,
                    created_at
                )
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (perm_id, item_id, principal_type, principal_id, role, created_at),
            )
            _record_activity(
                conn,
                item_id=item_id,
                event_type="permission.created",
                actor_user_id=actor_user_id,
                data={
                    "permission_id": perm_id,
                    "principal_type": principal_type,
                    "principal_id": principal_id,
                    "role": role,
                },
            )
        return jsonify(
            {
                "id": perm_id,
                "item_id": item_id,
                "principal_type": principal_type,
                "principal_id": principal_id,
                "role": role,
                "created_at": created_at,
            }
        ), 201

    @app.get("/items/<item_id>/permissions")
    @handler
    def list_permissions(item_id: str) -> Any:
        limit = parse_limit(request.args.get("limit"))
        cursor_raw = request.args.get("cursor")
        cursor = decode_cursor(cursor_raw) if cursor_raw else None
        with get_connection() as conn:
            item = conn.execute("SELECT id FROM items WHERE id = ?", (item_id,)).fetchone()
            if not item:
                return _json_error("Item not found", 404)
            if limit is None:
                rows = conn.execute(
                    "SELECT * FROM permissions WHERE item_id = ? ORDER BY created_at, id",
                    (item_id,),
                ).fetchall()
                return jsonify(
                    {
                        "permissions": [
                            {
                                "id": row["id"],
                                "item_id": row["item_id"],
                                "principal_type": row["principal_type"],
                                "principal_id": row["principal_id"],
                                "role": row["role"],
                                "created_at": row["created_at"],
                            }
                            for row in rows
                        ]
                    }
                )
            rows, next_cursor = _paginate_rows_asc(
                conn,
                table="permissions",
                where=["item_id = ?"],
                params=[item_id],
                limit=limit,
                cursor=cursor,
            )
            return jsonify(
                {
                    "permissions": [
                        {
                            "id": row["id"],
                            "item_id": row["item_id"],
                            "principal_type": row["principal_type"],
                            "principal_id": row["principal_id"],
                            "role": row["role"],
                            "created_at": row["created_at"],
                        }
                        for row in rows
                    ],
                    "next_cursor": next_cursor,
                }
            )

    @app.delete("/items/<item_id>/permissions/<permission_id>")
    def delete_permission(item_id: str, permission_id: str) -> Any:
        with get_connection() as conn:
            item = conn.execute("SELECT id FROM items WHERE id = ?", (item_id,)).fetchone()
            if not item:
                return _json_error("Item not found", 404)
            existing = conn.execute(
                "SELECT * FROM permissions WHERE id = ? AND item_id = ?",
                (permission_id, item_id),
            ).fetchone()
            conn.execute(
                "DELETE FROM permissions WHERE id = ? AND item_id = ?",
                (permission_id, item_id),
            )
            if existing:
                _record_activity(
                    conn,
                    item_id=item_id,
                    event_type="permission.deleted",
                    actor_user_id=None,
                    data={
                        "permission_id": permission_id,
                        "principal_type": existing["principal_type"],
                        "principal_id": existing["principal_id"],
                        "role": existing["role"],
                    },
                )
            rows = conn.execute(
                "SELECT * FROM permissions WHERE item_id = ?",
                (item_id,),
            ).fetchall()
        return jsonify(
            {
                "permissions": [
                    {
                        "id": row["id"],
                        "item_id": row["item_id"],
                        "principal_type": row["principal_type"],
                        "principal_id": row["principal_id"],
                        "role": row["role"],
                        "created_at": row["created_at"],
                    }
                    for row in rows
                ]
            }
        )

    @app.post("/items/<item_id>/share-links")
    @handler
    def create_share_link(item_id: str) -> Any:
        payload = request.get_json(silent=True) or {}
        actor_user_id = _optional_str(payload, "actor_user_id")
        role = _parse_role(_require_str(payload, "role"))
        expires_at = _optional_str(payload, "expires_at")

        with get_connection() as conn:
            item = conn.execute("SELECT id FROM items WHERE id = ?", (item_id,)).fetchone()
            if not item:
                return _json_error("Item not found", 404)
            if actor_user_id:
                actor = conn.execute(
                    "SELECT id FROM users WHERE id = ?",
                    (actor_user_id,),
                ).fetchone()
                if not actor:
                    return _json_error("Actor not found", 404)
            link_id = str(uuid4())
            created_at = _now()
            token = secrets.token_urlsafe(16)
            conn.execute(
                """
                INSERT INTO share_links (id, item_id, token, role, expires_at, created_at)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (link_id, item_id, token, role, expires_at, created_at),
            )
            _record_activity(
                conn,
                item_id=item_id,
                event_type="share_link.created",
                actor_user_id=actor_user_id,
                data={"share_link_id": link_id, "role": role, "expires_at": expires_at},
            )
        return jsonify(
            {
                "id": link_id,
                "item_id": item_id,
                "token": token,
                "role": role,
                "expires_at": expires_at,
                "created_at": created_at,
            }
        ), 201

    @app.get("/items/<item_id>/share-links")
    @handler
    def list_share_links(item_id: str) -> Any:
        limit = parse_limit(request.args.get("limit"))
        cursor_raw = request.args.get("cursor")
        cursor = decode_cursor(cursor_raw) if cursor_raw else None
        with get_connection() as conn:
            item = conn.execute("SELECT id FROM items WHERE id = ?", (item_id,)).fetchone()
            if not item:
                return _json_error("Item not found", 404)
            if limit is None:
                rows = conn.execute(
                    "SELECT * FROM share_links WHERE item_id = ? ORDER BY created_at, id",
                    (item_id,),
                ).fetchall()
                return jsonify(
                    {
                        "share_links": [
                            {
                                "id": row["id"],
                                "item_id": row["item_id"],
                                "token": row["token"],
                                "role": row["role"],
                                "expires_at": row["expires_at"],
                                "created_at": row["created_at"],
                            }
                            for row in rows
                        ]
                    }
                )
            rows, next_cursor = _paginate_rows_asc(
                conn,
                table="share_links",
                where=["item_id = ?"],
                params=[item_id],
                limit=limit,
                cursor=cursor,
            )
            return jsonify(
                {
                    "share_links": [
                        {
                            "id": row["id"],
                            "item_id": row["item_id"],
                            "token": row["token"],
                            "role": row["role"],
                            "expires_at": row["expires_at"],
                            "created_at": row["created_at"],
                        }
                        for row in rows
                    ],
                    "next_cursor": next_cursor,
                }
            )

    @app.delete("/items/<item_id>/share-links/<link_id>")
    def delete_share_link(item_id: str, link_id: str) -> Any:
        with get_connection() as conn:
            item = conn.execute("SELECT id FROM items WHERE id = ?", (item_id,)).fetchone()
            if not item:
                return _json_error("Item not found", 404)
            existing = conn.execute(
                "SELECT * FROM share_links WHERE id = ? AND item_id = ?",
                (link_id, item_id),
            ).fetchone()
            conn.execute(
                "DELETE FROM share_links WHERE id = ? AND item_id = ?",
                (link_id, item_id),
            )
            if existing:
                _record_activity(
                    conn,
                    item_id=item_id,
                    event_type="share_link.deleted",
                    actor_user_id=None,
                    data={
                        "share_link_id": link_id,
                        "role": existing["role"],
                        "expires_at": existing["expires_at"],
                    },
                )
            rows = conn.execute(
                "SELECT * FROM share_links WHERE item_id = ?",
                (item_id,),
            ).fetchall()
        return jsonify(
            {
                "share_links": [
                    {
                        "id": row["id"],
                        "item_id": row["item_id"],
                        "token": row["token"],
                        "role": row["role"],
                        "expires_at": row["expires_at"],
                        "created_at": row["created_at"],
                    }
                    for row in rows
                ]
            }
        )

    @app.post("/items/<item_id>/comments")
    @handler
    def create_comment(item_id: str) -> Any:
        payload = request.get_json(silent=True) or {}
        author_user_id = _require_str(payload, "author_user_id")
        body = _require_str(payload, "body")

        with get_connection() as conn:
            item = conn.execute("SELECT id FROM items WHERE id = ?", (item_id,)).fetchone()
            if not item:
                return _json_error("Item not found", 404)
            user = conn.execute(
                "SELECT id FROM users WHERE id = ?",
                (author_user_id,),
            ).fetchone()
            if not user:
                return _json_error("User not found", 404)
            comment_id = str(uuid4())
            created_at = _now()
            conn.execute(
                """
                INSERT INTO comments (id, item_id, author_user_id, body, created_at)
                VALUES (?, ?, ?, ?, ?)
                """,
                (comment_id, item_id, author_user_id, body, created_at),
            )
            _record_activity(
                conn,
                item_id=item_id,
                event_type="comment.created",
                actor_user_id=author_user_id,
                data={"comment_id": comment_id, "body_length": len(body)},
            )
        return jsonify(
            {
                "id": comment_id,
                "item_id": item_id,
                "author_user_id": author_user_id,
                "body": body,
                "created_at": created_at,
            }
        ), 201

    @app.get("/items/<item_id>/comments")
    @handler
    def list_comments(item_id: str) -> Any:
        limit = parse_limit(request.args.get("limit"))
        cursor_raw = request.args.get("cursor")
        cursor = decode_cursor(cursor_raw) if cursor_raw else None
        with get_connection() as conn:
            item = conn.execute("SELECT id FROM items WHERE id = ?", (item_id,)).fetchone()
            if not item:
                return _json_error("Item not found", 404)
            if limit is None:
                rows = conn.execute(
                    "SELECT * FROM comments WHERE item_id = ? ORDER BY created_at, id",
                    (item_id,),
                ).fetchall()
                return jsonify(
                    {
                        "comments": [
                            {
                                "id": row["id"],
                                "item_id": row["item_id"],
                                "author_user_id": row["author_user_id"],
                                "body": row["body"],
                                "created_at": row["created_at"],
                            }
                            for row in rows
                        ]
                    }
                )
            rows, next_cursor = _paginate_rows_asc(
                conn,
                table="comments",
                where=["item_id = ?"],
                params=[item_id],
                limit=limit,
                cursor=cursor,
            )
            return jsonify(
                {
                    "comments": [
                        {
                            "id": row["id"],
                            "item_id": row["item_id"],
                            "author_user_id": row["author_user_id"],
                            "body": row["body"],
                            "created_at": row["created_at"],
                        }
                        for row in rows
                    ],
                    "next_cursor": next_cursor,
                }
            )

    @app.get("/search")
    @handler
    def search_items() -> Any:
        q = request.args.get("q", "").strip()
        if not q:
            raise ValueError("q is required")
        limit = parse_limit(request.args.get("limit"))
        cursor_raw = request.args.get("cursor")
        cursor = decode_cursor(cursor_raw) if cursor_raw else None
        like = f"%{q}%"
        with get_connection() as conn:
            where = "(name LIKE ? OR content_text LIKE ? OR content_json LIKE ?)"
            if limit is None:
                rows = conn.execute(
                    f"SELECT * FROM items WHERE {where} ORDER BY created_at, id",
                    (like, like, like),
                ).fetchall()
                return jsonify({"items": [_row_to_item(row) for row in rows]})
            rows, next_cursor = _paginate_rows_asc(
                conn,
                table="items",
                where=[where],
                params=[like, like, like],
                limit=limit,
                cursor=cursor,
            )
            return jsonify(
                {"items": [_row_to_item(row) for row in rows], "next_cursor": next_cursor}
            )

    @app.get("/items/<item_id>/activity")
    @handler
    def list_activity(item_id: str) -> Any:
        limit = parse_limit(request.args.get("limit")) or 50
        cursor_raw = request.args.get("cursor")
        cursor = decode_cursor(cursor_raw) if cursor_raw else None

        before = request.args.get("before")
        before = before.strip() if before else None
        if before and cursor is None:
            cursor = Cursor(created_at=before, id="")

        with get_connection() as conn:
            item = conn.execute("SELECT id FROM items WHERE id = ?", (item_id,)).fetchone()
            if not item:
                return _json_error("Item not found", 404)

            rows, next_cursor = _paginate_rows_desc(
                conn,
                table="activities",
                where=["item_id = ?"],
                params=[item_id],
                limit=limit,
                cursor=cursor,
            )

        events: list[dict[str, Any]] = []
        for row in rows:
            data_json = row["data_json"]
            data = json.loads(data_json) if data_json else {}
            events.append(
                {
                    "id": row["id"],
                    "item_id": row["item_id"],
                    "event_type": row["event_type"],
                    "actor_user_id": row["actor_user_id"],
                    "data": data,
                    "created_at": row["created_at"],
                }
            )
        return jsonify({"events": events, "next_cursor": next_cursor})
