from __future__ import annotations

import json
import secrets
import sqlite3
from datetime import UTC, datetime
from typing import Any, Callable
from uuid import uuid4

from flask import Flask, jsonify, request

from .db import get_connection
from .schemas import ItemType, PrincipalType, RoleType
from .snapshot import export_snapshot, import_snapshot

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


def register_routes(app: Flask) -> None:
    def handler(fn: Callable[..., Any]) -> Callable[..., Any]:
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            try:
                return fn(*args, **kwargs)
            except ValueError as exc:
                return _json_error(str(exc), 400)

        wrapper.__name__ = fn.__name__
        return wrapper

    @app.get("/health")
    def health() -> Any:
        return jsonify({"status": "ok"})

    @app.get("/stats")
    def stats() -> Any:
        with get_connection() as conn:
            users = conn.execute("SELECT COUNT(*) FROM users").fetchone()[0]
            groups = conn.execute("SELECT COUNT(*) FROM groups").fetchone()[0]
            items = conn.execute("SELECT COUNT(*) FROM items").fetchone()[0]
            permissions = conn.execute("SELECT COUNT(*) FROM permissions").fetchone()[0]
            share_links = conn.execute("SELECT COUNT(*) FROM share_links").fetchone()[0]
            comments = conn.execute("SELECT COUNT(*) FROM comments").fetchone()[0]
        return jsonify(
            {
                "users": users,
                "groups": groups,
                "items": items,
                "permissions": permissions,
                "share_links": share_links,
                "comments": comments,
            }
        )

    @app.get("/snapshot")
    def get_snapshot() -> Any:
        with get_connection() as conn:
            return jsonify(export_snapshot(conn))

    @app.post("/snapshot")
    @handler
    def post_snapshot() -> Any:
        mode = request.args.get("mode", "replace")
        payload = request.get_json(silent=True)
        if payload is None:
            raise ValueError("JSON body required")
        if not isinstance(payload, dict):
            raise ValueError("Body must be an object")

        with get_connection() as conn:
            inserted = import_snapshot(conn, payload, mode=mode)
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
    def list_users() -> Any:
        with get_connection() as conn:
            rows = conn.execute("SELECT * FROM users ORDER BY created_at").fetchall()
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
    def list_groups() -> Any:
        with get_connection() as conn:
            rows = conn.execute("SELECT * FROM groups ORDER BY created_at").fetchall()
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
            existing = conn.execute(
                "SELECT id FROM group_members WHERE group_id = ? AND user_id = ?",
                (group_id, user_id),
            ).fetchone()
            if not existing:
                conn.execute(
                    "INSERT INTO group_members (id, group_id, user_id, created_at) "
                    "VALUES (?, ?, ?, ?)",
                    (str(uuid4()), group_id, user_id, _now()),
                )
            return jsonify(
                {
                    "id": group["id"],
                    "name": group["name"],
                    "description": group["description"],
                    "created_at": group["created_at"],
                }
            ), 201

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
        sheet_data = payload.get("sheet_data")
        if sheet_data is not None and not isinstance(sheet_data, dict):
            raise ValueError("sheet_data must be an object")

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

            if item_type == "doc":
                content_text = content_text or ""
            content_json = None
            if item_type == "sheet":
                content_json = json.dumps(sheet_data or {})

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
            row = conn.execute("SELECT * FROM items WHERE id = ?", (item_id,)).fetchone()
        return jsonify(_row_to_item(row)), 201

    @app.get("/items")
    def list_items() -> Any:
        parent_id = request.args.get("parent_id")
        with get_connection() as conn:
            if parent_id is None:
                rows = conn.execute("SELECT * FROM items ORDER BY created_at").fetchall()
            else:
                rows = conn.execute(
                    "SELECT * FROM items WHERE parent_id = ? ORDER BY created_at",
                    (parent_id,),
                ).fetchall()
        return jsonify({"items": [_row_to_item(row) for row in rows]})

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
        with get_connection() as conn:
            row = conn.execute("SELECT * FROM items WHERE id = ?", (item_id,)).fetchone()
            if not row:
                return _json_error("Item not found", 404)
            if row["item_type"] == "doc":
                content_text = _optional_str(payload, "content_text")
                if content_text is None:
                    raise ValueError("content_text required for docs")
                conn.execute(
                    "UPDATE items SET content_text = ?, updated_at = ? WHERE id = ?",
                    (content_text, _now(), item_id),
                )
            elif row["item_type"] == "sheet":
                sheet_data = payload.get("sheet_data")
                if sheet_data is None or not isinstance(sheet_data, dict):
                    raise ValueError("sheet_data required for sheets")
                conn.execute(
                    "UPDATE items SET content_json = ?, updated_at = ? WHERE id = ?",
                    (json.dumps(sheet_data), _now(), item_id),
                )
            else:
                return _json_error("Folders have no content", 400)
            row = conn.execute("SELECT * FROM items WHERE id = ?", (item_id,)).fetchone()
        return jsonify(_row_to_item(row))

    @app.post("/items/<item_id>/permissions")
    @handler
    def create_permission(item_id: str) -> Any:
        payload = request.get_json(silent=True) or {}
        principal_type = _parse_principal_type(_require_str(payload, "principal_type"))
        principal_id = _optional_str(payload, "principal_id")
        role = _parse_role(_require_str(payload, "role"))

        with get_connection() as conn:
            item = conn.execute("SELECT id FROM items WHERE id = ?", (item_id,)).fetchone()
            if not item:
                return _json_error("Item not found", 404)
            if principal_type == "user":
                if not principal_id:
                    raise ValueError("principal_id required")
                user = conn.execute(
                    "SELECT id FROM users WHERE id = ?",
                    (principal_id,),
                ).fetchone()
                if not user:
                    return _json_error("User not found", 404)
            if principal_type == "group":
                if not principal_id:
                    raise ValueError("principal_id required")
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
    def list_permissions(item_id: str) -> Any:
        with get_connection() as conn:
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

    @app.delete("/items/<item_id>/permissions/<permission_id>")
    def delete_permission(item_id: str, permission_id: str) -> Any:
        with get_connection() as conn:
            conn.execute(
                "DELETE FROM permissions WHERE id = ? AND item_id = ?",
                (permission_id, item_id),
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
        role = _parse_role(_require_str(payload, "role"))
        expires_at = _optional_str(payload, "expires_at")

        with get_connection() as conn:
            item = conn.execute("SELECT id FROM items WHERE id = ?", (item_id,)).fetchone()
            if not item:
                return _json_error("Item not found", 404)
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
    def list_share_links(item_id: str) -> Any:
        with get_connection() as conn:
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

    @app.delete("/items/<item_id>/share-links/<link_id>")
    def delete_share_link(item_id: str, link_id: str) -> Any:
        with get_connection() as conn:
            conn.execute(
                "DELETE FROM share_links WHERE id = ? AND item_id = ?",
                (link_id, item_id),
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
    def list_comments(item_id: str) -> Any:
        with get_connection() as conn:
            rows = conn.execute("SELECT * FROM comments WHERE item_id = ?", (item_id,)).fetchall()
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

    @app.get("/search")
    @handler
    def search_items() -> Any:
        q = request.args.get("q", "").strip()
        if not q:
            raise ValueError("q is required")
        like = f"%{q}%"
        with get_connection() as conn:
            rows = conn.execute(
                """
                SELECT * FROM items
                WHERE name LIKE ? OR content_text LIKE ? OR content_json LIKE ?
                ORDER BY created_at
                """,
                (like, like, like),
            ).fetchall()
        return jsonify({"items": [_row_to_item(row) for row in rows]})
