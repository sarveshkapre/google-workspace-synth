from __future__ import annotations

import gzip
import importlib
import json
import time


def _build_client(db_path, monkeypatch, env: dict[str, str] | None = None):
    monkeypatch.setenv("GWSYNTH_DB_PATH", str(db_path))
    if env:
        for key, value in env.items():
            monkeypatch.setenv(key, value)
    import gwsynth.main

    importlib.reload(gwsynth.main)
    app = gwsynth.main.create_app()
    app.config.update(TESTING=True)
    return app.test_client()


def test_end_to_end(tmp_path, monkeypatch):
    client = _build_client(tmp_path / "test.db", monkeypatch)

    user_resp = client.post(
        "/users", json={"email": "demo@example.com", "display_name": "Demo User"}
    )
    assert user_resp.status_code == 201
    user = user_resp.get_json()
    assert user["email"] == "demo@example.com"

    group_resp = client.post("/groups", json={"name": "Team", "description": "Core team"})
    assert group_resp.status_code == 201
    group = group_resp.get_json()
    client.post(f"/groups/{group['id']}/members", json={"user_id": user["id"]})

    folder = client.post(
        "/items",
        json={"name": "Root", "item_type": "folder", "owner_user_id": user["id"]},
    ).get_json()
    doc = client.post(
        "/items",
        json={
            "name": "Spec",
            "item_type": "doc",
            "parent_id": folder["id"],
            "owner_user_id": user["id"],
            "content_text": "Hello",
        },
    ).get_json()

    updated = client.put(
        f"/items/{doc['id']}/content", json={"content_text": "Updated"}
    ).get_json()
    assert updated["content_text"] == "Updated"

    permission = client.post(
        f"/items/{doc['id']}/permissions",
        json={"principal_type": "group", "principal_id": group["id"], "role": "viewer"},
    ).get_json()
    assert permission["role"] == "viewer"

    link = client.post(
        f"/items/{doc['id']}/share-links", json={"role": "viewer"}
    ).get_json()
    assert link["token"]

    results = client.get("/search", query_string={"q": "Spec"}).get_json()
    assert results["items"]


def test_snapshot_export_import(tmp_path, monkeypatch):
    client1 = _build_client(tmp_path / "db1.db", monkeypatch)

    user = client1.post(
        "/users", json={"email": "snap@example.com", "display_name": "Snap User"}
    ).get_json()
    folder = client1.post(
        "/items",
        json={"name": "Root", "item_type": "folder", "owner_user_id": user["id"]},
    ).get_json()
    client1.post(
        "/items",
        json={
            "name": "Snap Doc",
            "item_type": "doc",
            "parent_id": folder["id"],
            "owner_user_id": user["id"],
            "content_text": "Hello snapshot",
        },
    )

    snapshot = client1.get("/snapshot").get_json()
    assert snapshot["snapshot_version"] == 2

    client2 = _build_client(tmp_path / "db2.db", monkeypatch)
    imported = client2.post("/snapshot?mode=replace", json=snapshot).get_json()
    assert imported["status"] == "imported"

    users = client2.get("/users").get_json()
    assert any(u["email"] == "snap@example.com" for u in users)


def test_snapshot_tables_filter_and_replace_tables_mode(tmp_path, monkeypatch):
    client1 = _build_client(tmp_path / "db1.db", monkeypatch)
    user = client1.post(
        "/users", json={"email": "snap2@example.com", "display_name": "Snap2 User"}
    ).get_json()
    client1.post(
        "/items",
        json={"name": "Root", "item_type": "folder", "owner_user_id": user["id"]},
    )

    snapshot = client1.get("/snapshot?tables=users,items").get_json()
    assert snapshot["exported_tables"] == ["users", "items"]
    assert set(snapshot["tables"].keys()) == {"users", "items"}

    client2 = _build_client(tmp_path / "db2.db", monkeypatch)
    # Full replace should reject partial snapshots.
    resp = client2.post("/snapshot?mode=replace", json=snapshot)
    assert resp.status_code == 400

    imported = client2.post(
        "/snapshot?mode=replace_tables&tables=users,items",
        json=snapshot,
    ).get_json()
    assert imported["status"] == "imported"
    users = client2.get("/users").get_json()
    assert any(u["email"] == "snap2@example.com" for u in users)


def test_snapshot_schema_mismatch_is_rejected(tmp_path, monkeypatch):
    client1 = _build_client(tmp_path / "db1.db", monkeypatch)
    client1.post("/users", json={"email": "schema@example.com", "display_name": "Schema User"})
    snapshot = client1.get("/snapshot").get_json()
    # Tamper with schema to reference a missing column.
    snapshot["schema"]["users"].append("does_not_exist")

    client2 = _build_client(tmp_path / "db2.db", monkeypatch)
    resp = client2.post("/snapshot?mode=replace", json=snapshot)
    assert resp.status_code == 400


def test_snapshot_gzip_stream(tmp_path, monkeypatch):
    client = _build_client(tmp_path / "gzip.db", monkeypatch)
    client.post("/users", json={"email": "zip@example.com", "display_name": "Zip User"})

    resp = client.get("/snapshot", query_string={"gzip": "1"})
    assert resp.status_code == 200
    assert resp.headers.get("Content-Encoding") == "gzip"

    payload = json.loads(gzip.decompress(resp.data).decode("utf-8"))
    assert payload["snapshot_version"] == 2
    assert "tables" in payload


def test_snapshot_import_accepts_gzip_content_encoding(tmp_path, monkeypatch):
    client1 = _build_client(tmp_path / "db1.db", monkeypatch)
    client1.post("/users", json={"email": "zipin@example.com", "display_name": "ZipIn User"})
    snapshot = client1.get("/snapshot").get_json()

    gz = gzip.compress(json.dumps(snapshot).encode("utf-8"))

    client2 = _build_client(tmp_path / "db2.db", monkeypatch)
    imported = client2.post(
        "/snapshot?mode=replace",
        data=gz,
        headers={"Content-Type": "application/json", "Content-Encoding": "gzip"},
    )
    assert imported.status_code == 200
    assert imported.get_json()["status"] == "imported"


def test_snapshot_import_gzip_respects_decompressed_limit(tmp_path, monkeypatch):
    client1 = _build_client(tmp_path / "db1.db", monkeypatch)
    client1.post("/users", json={"email": "ziplimit@example.com", "display_name": "ZipLimit"})
    snapshot = client1.get("/snapshot").get_json()
    gz = gzip.compress(json.dumps(snapshot).encode("utf-8"))

    client2 = _build_client(
        tmp_path / "db2.db",
        monkeypatch,
        env={"GWSYNTH_SNAPSHOT_MAX_DECOMPRESSED_BYTES": "10"},
    )
    resp = client2.post(
        "/snapshot?mode=replace",
        data=gz,
        headers={"Content-Type": "application/json", "Content-Encoding": "gzip"},
    )
    assert resp.status_code == 400
    assert "Decompressed snapshot body exceeds" in resp.get_json()["error"]


def test_snapshot_etag_if_none_match(tmp_path, monkeypatch):
    client = _build_client(tmp_path / "etag.db", monkeypatch)
    client.post("/users", json={"email": "etag@example.com", "display_name": "Etag User"})

    resp1 = client.get("/snapshot")
    assert resp1.status_code == 200
    etag = resp1.headers.get("ETag")
    assert etag

    resp2 = client.get("/snapshot", headers={"If-None-Match": etag})
    assert resp2.status_code == 304
    assert resp2.data == b""

    time.sleep(0.01)
    client.post("/users", json={"email": "etag2@example.com", "display_name": "Etag2 User"})
    resp3 = client.get("/snapshot")
    assert resp3.status_code == 200
    etag2 = resp3.headers.get("ETag")
    assert etag2 and etag2 != etag


def test_request_entity_too_large_is_json(tmp_path, monkeypatch):
    client = _build_client(
        tmp_path / "limit.db",
        monkeypatch,
        env={"GWSYNTH_MAX_REQUEST_BYTES": "50"},
    )
    resp = client.post(
        "/snapshot?mode=replace",
        data=b'{"a":"' + (b"x" * 200) + b'"}',
        headers={"Content-Type": "application/json"},
    )
    assert resp.status_code == 413
    body = resp.get_json()
    assert body["error"]
    assert "GWSYNTH_MAX_REQUEST_BYTES" in body["hint"]


def test_openapi_and_docs_endpoints(tmp_path, monkeypatch):
    client = _build_client(tmp_path / "docs.db", monkeypatch)

    index = client.get("/")
    assert index.status_code == 200
    assert "text/html" in (index.content_type or "")

    spec = client.get("/openapi.json").get_json()
    assert spec["openapi"].startswith("3.")
    assert spec["info"]["title"]
    assert spec["security"] == [{"ApiKeyAuth": []}, {"BearerAuth": []}]
    assert "securitySchemes" in spec["components"]
    assert "ApiKeyAuth" in spec["components"]["securitySchemes"]
    assert "BearerAuth" in spec["components"]["securitySchemes"]
    assert spec["paths"]["/health"]["get"].get("security") == []
    assert spec["paths"]["/stats"]["get"].get("security") == []
    assert (
        spec["paths"]["/items"]["get"]["responses"]["200"]["content"]["application/json"][
            "schema"
        ]["$ref"]
        == "#/components/schemas/ItemsList"
    )
    assert (
        spec["paths"]["/items/{item_id}/permissions"]["get"]["responses"]["200"]["content"][
            "application/json"
        ]["schema"]["$ref"]
        == "#/components/schemas/PermissionsList"
    )
    assert "GroupMembersPage" in spec["components"]["schemas"]
    assert "ShareLinksList" in spec["components"]["schemas"]

    docs = client.get("/docs")
    assert docs.status_code == 200
    assert "text/html" in (docs.content_type or "")
    assert "persistAuthorization" in docs.data.decode("utf-8")


def test_docs_local_mode_uses_vendored_assets(tmp_path, monkeypatch):
    assets_dir = tmp_path / "swagger-assets"
    assets_dir.mkdir()
    (assets_dir / "swagger-ui.css").write_text("/* css */", encoding="utf-8")
    (assets_dir / "swagger-ui-bundle.js").write_text("// js", encoding="utf-8")

    client = _build_client(
        tmp_path / "docs_local.db",
        monkeypatch,
        env={
            "GWSYNTH_SWAGGER_UI_MODE": "local",
            "GWSYNTH_SWAGGER_UI_LOCAL_DIR": str(assets_dir),
        },
    )

    docs = client.get("/docs")
    assert docs.status_code == 200
    html = docs.data.decode("utf-8")
    assert "/docs-assets/swagger-ui.css" in html
    assert "/docs-assets/swagger-ui-bundle.js" in html

    css = client.get("/docs-assets/swagger-ui.css")
    assert css.status_code == 200
    assert "text/css" in (css.content_type or "")
    assert css.data.decode("utf-8") == "/* css */"

    bundle = client.get("/docs-assets/swagger-ui-bundle.js")
    assert bundle.status_code == 200
    assert bundle.data.decode("utf-8") == "// js"


def test_docs_local_mode_missing_assets_returns_503(tmp_path, monkeypatch):
    client = _build_client(
        tmp_path / "docs_local_missing.db",
        monkeypatch,
        env={
            "GWSYNTH_SWAGGER_UI_MODE": "local",
            "GWSYNTH_SWAGGER_UI_LOCAL_DIR": str(tmp_path / "missing-assets"),
        },
    )

    docs = client.get("/docs")
    assert docs.status_code == 503
    body = docs.data.decode("utf-8")
    assert "Swagger UI assets not found" in body
    assert "vendor_swagger_ui.py" in body


def test_api_key_auth_allows_docs_and_openapi(tmp_path, monkeypatch):
    client = _build_client(
        tmp_path / "auth.db",
        monkeypatch,
        env={"GWSYNTH_API_KEY": "secret"},
    )

    assert client.get("/").status_code == 200
    assert client.get("/health").status_code == 200
    assert client.get("/docs").status_code == 200
    assert client.get("/openapi.json").status_code == 200
    assert client.get("/stats").status_code == 200

    assert client.get("/users").status_code == 401
    assert client.get("/users", headers={"X-API-Key": "secret"}).status_code == 200


def test_api_key_auth_allows_docs_assets(tmp_path, monkeypatch):
    assets_dir = tmp_path / "auth-docs-assets"
    assets_dir.mkdir()
    (assets_dir / "swagger-ui.css").write_text("/* auth css */", encoding="utf-8")
    (assets_dir / "swagger-ui-bundle.js").write_text("// auth js", encoding="utf-8")

    client = _build_client(
        tmp_path / "auth_docs_assets.db",
        monkeypatch,
        env={
            "GWSYNTH_API_KEY": "secret",
            "GWSYNTH_SWAGGER_UI_MODE": "local",
            "GWSYNTH_SWAGGER_UI_LOCAL_DIR": str(assets_dir),
        },
    )

    assert client.get("/docs-assets/swagger-ui.css").status_code == 200
    assert client.get("/docs-assets/swagger-ui-bundle.js").status_code == 200
    assert client.get("/users").status_code == 401


def test_rate_limiting(tmp_path, monkeypatch):
    client = _build_client(
        tmp_path / "ratelimit.db",
        monkeypatch,
        env={
            "GWSYNTH_RATE_LIMIT_ENABLED": "1",
            "GWSYNTH_RATE_LIMIT_RPM": "1",
            "GWSYNTH_RATE_LIMIT_BURST": "1",
        },
    )
    assert client.get("/health").status_code == 200
    assert client.get("/users").status_code == 200
    throttled = client.get("/users")
    assert throttled.status_code == 429
    assert throttled.headers.get("X-RateLimit-Limit") == "1"
    assert throttled.headers.get("X-RateLimit-Remaining") == "0"
    retry_after = int(throttled.headers.get("Retry-After", "0"))
    assert 1 <= retry_after <= 60


def test_rate_limiting_does_not_trust_x_forwarded_for_by_default(tmp_path, monkeypatch):
    client = _build_client(
        tmp_path / "ratelimit_xff.db",
        monkeypatch,
        env={
            "GWSYNTH_RATE_LIMIT_ENABLED": "1",
            "GWSYNTH_RATE_LIMIT_RPM": "1",
            "GWSYNTH_RATE_LIMIT_BURST": "1",
        },
    )

    # If we trusted X-Forwarded-For by default, swapping this header would evade the limiter.
    assert client.get("/users", headers={"X-Forwarded-For": "1.1.1.1"}).status_code == 200
    assert client.get("/users", headers={"X-Forwarded-For": "2.2.2.2"}).status_code == 429


def test_rate_limiting_can_trust_x_forwarded_for_when_enabled(tmp_path, monkeypatch):
    client = _build_client(
        tmp_path / "ratelimit_trust_proxy.db",
        monkeypatch,
        env={
            "GWSYNTH_RATE_LIMIT_ENABLED": "1",
            "GWSYNTH_RATE_LIMIT_RPM": "1",
            "GWSYNTH_RATE_LIMIT_BURST": "1",
            "GWSYNTH_TRUST_PROXY": "1",
        },
    )

    assert client.get("/users", headers={"X-Forwarded-For": "1.1.1.1"}).status_code == 200
    assert client.get("/users", headers={"X-Forwarded-For": "1.1.1.1"}).status_code == 429
    # Different forwarded IP should be tracked separately when explicitly enabled.
    assert client.get("/users", headers={"X-Forwarded-For": "2.2.2.2"}).status_code == 200


def test_rate_limiting_prefers_forwarded_header_when_trust_proxy_enabled(tmp_path, monkeypatch):
    client = _build_client(
        tmp_path / "ratelimit_forwarded.db",
        monkeypatch,
        env={
            "GWSYNTH_RATE_LIMIT_ENABLED": "1",
            "GWSYNTH_RATE_LIMIT_RPM": "1",
            "GWSYNTH_RATE_LIMIT_BURST": "1",
            "GWSYNTH_TRUST_PROXY": "1",
        },
    )

    headers1 = {"Forwarded": "for=1.1.1.1", "X-Forwarded-For": "9.9.9.9"}
    headers2 = {"Forwarded": "for=2.2.2.2", "X-Forwarded-For": "1.1.1.1"}

    assert client.get("/users", headers=headers1).status_code == 200
    assert client.get("/users", headers=headers1).status_code == 429
    # Different RFC 7239 `for` value should be tracked as a different client.
    assert client.get("/users", headers=headers2).status_code == 200


def test_rate_limiting_uses_x_real_ip_as_proxy_fallback(tmp_path, monkeypatch):
    client = _build_client(
        tmp_path / "ratelimit_x_real_ip.db",
        monkeypatch,
        env={
            "GWSYNTH_RATE_LIMIT_ENABLED": "1",
            "GWSYNTH_RATE_LIMIT_RPM": "1",
            "GWSYNTH_RATE_LIMIT_BURST": "1",
            "GWSYNTH_TRUST_PROXY": "1",
        },
    )

    assert client.get("/users", headers={"X-Real-IP": "1.1.1.1"}).status_code == 200
    assert client.get("/users", headers={"X-Real-IP": "1.1.1.1"}).status_code == 429
    assert client.get("/users", headers={"X-Real-IP": "2.2.2.2"}).status_code == 200


def test_item_activity_timeline(tmp_path, monkeypatch):
    client = _build_client(tmp_path / "activity.db", monkeypatch)

    user = client.post(
        "/users", json={"email": "act@example.com", "display_name": "Act User"}
    ).get_json()
    folder = client.post(
        "/items",
        json={"name": "Root", "item_type": "folder", "owner_user_id": user["id"]},
    ).get_json()
    doc = client.post(
        "/items",
        json={
            "name": "Act Doc",
            "item_type": "doc",
            "parent_id": folder["id"],
            "owner_user_id": user["id"],
            "content_text": "Hello",
        },
    ).get_json()

    client.put(
        f"/items/{doc['id']}/content",
        json={"content_text": "Updated", "actor_user_id": user["id"]},
    )
    client.post(
        f"/items/{doc['id']}/permissions",
        json={
            "principal_type": "anyone",
            "role": "viewer",
            "actor_user_id": user["id"],
        },
    )
    client.post(
        f"/items/{doc['id']}/share-links",
        json={"role": "viewer", "actor_user_id": user["id"]},
    )
    client.post(
        f"/items/{doc['id']}/comments",
        json={"author_user_id": user["id"], "body": "Looks good"},
    )

    timeline = client.get(f"/items/{doc['id']}/activity").get_json()
    event_types = {e["event_type"] for e in timeline["events"]}
    assert "item.created" in event_types
    assert "item.content_updated" in event_types
    assert "permission.created" in event_types
    assert "share_link.created" in event_types
    assert "comment.created" in event_types


def test_pagination_users(tmp_path, monkeypatch):
    client = _build_client(tmp_path / "paging.db", monkeypatch)

    for i in range(3):
        resp = client.post(
            "/users",
            json={"email": f"u{i}@example.com", "display_name": f"User {i}"},
        )
        assert resp.status_code == 201

    page1 = client.get("/users", query_string={"limit": 2}).get_json()
    assert len(page1["users"]) == 2
    assert page1["next_cursor"]

    page2 = client.get(
        "/users", query_string={"limit": 2, "cursor": page1["next_cursor"]}
    ).get_json()
    assert len(page2["users"]) == 1


def test_items_filtering(tmp_path, monkeypatch):
    client = _build_client(tmp_path / "filters.db", monkeypatch)

    alice = client.post(
        "/users", json={"email": "alice@example.com", "display_name": "Alice"}
    ).get_json()
    bob = client.post("/users", json={"email": "bob@example.com", "display_name": "Bob"}).get_json()

    root = client.post(
        "/items",
        json={"name": "Root", "item_type": "folder", "owner_user_id": alice["id"]},
    ).get_json()
    client.post(
        "/items",
        json={
            "name": "Alice Doc",
            "item_type": "doc",
            "parent_id": root["id"],
            "owner_user_id": alice["id"],
            "content_text": "Hi",
        },
    )
    client.post(
        "/items",
        json={
            "name": "Bob Sheet",
            "item_type": "sheet",
            "parent_id": root["id"],
            "owner_user_id": bob["id"],
            "sheet_data": {"A1": "1"},
        },
    )

    by_alice = client.get("/items", query_string={"owner_user_id": alice["id"]}).get_json()
    assert all(item["owner_user_id"] == alice["id"] for item in by_alice["items"])

    docs = client.get("/items", query_string={"item_type": "doc"}).get_json()
    assert all(item["item_type"] == "doc" for item in docs["items"])

    children = client.get("/items", query_string={"parent_id": root["id"]}).get_json()
    assert all(item["parent_id"] == root["id"] for item in children["items"])


def test_group_members_listing_and_idempotent_add(tmp_path, monkeypatch):
    client = _build_client(tmp_path / "group_members.db", monkeypatch)

    user1 = client.post(
        "/users", json={"email": "gm1@example.com", "display_name": "GM One"}
    ).get_json()
    user2 = client.post(
        "/users", json={"email": "gm2@example.com", "display_name": "GM Two"}
    ).get_json()
    group = client.post("/groups", json={"name": "Ops", "description": "Ops team"}).get_json()

    assert (
        client.post(f"/groups/{group['id']}/members", json={"user_id": user1["id"]}).status_code
        == 201
    )
    assert (
        client.post(f"/groups/{group['id']}/members", json={"user_id": user2["id"]}).status_code
        == 201
    )
    assert (
        client.post(f"/groups/{group['id']}/members", json={"user_id": user1["id"]}).status_code
        == 201
    )

    members = client.get(f"/groups/{group['id']}/members").get_json()
    assert len(members["members"]) == 2
    assert {member["email"] for member in members["members"]} == {
        "gm1@example.com",
        "gm2@example.com",
    }

    page1 = client.get(
        f"/groups/{group['id']}/members", query_string={"limit": 1}
    ).get_json()
    assert len(page1["members"]) == 1
    assert page1["next_cursor"]

    page2 = client.get(
        f"/groups/{group['id']}/members",
        query_string={"limit": 1, "cursor": page1["next_cursor"]},
    ).get_json()
    assert len(page2["members"]) == 1

    assert client.get("/groups/missing/members").status_code == 404


def test_invalid_query_params_return_400(tmp_path, monkeypatch):
    client = _build_client(tmp_path / "invalid_query_params.db", monkeypatch)

    user = client.post(
        "/users", json={"email": "qp@example.com", "display_name": "Query Params"}
    ).get_json()
    group = client.post(
        "/groups", json={"name": "Query Group", "description": "validation"}
    ).get_json()
    item = client.post(
        "/items",
        json={
            "name": "Query Doc",
            "item_type": "doc",
            "owner_user_id": user["id"],
            "content_text": "hello",
        },
    ).get_json()

    for path, query in [
        ("/users", {"limit": "abc"}),
        ("/groups", {"cursor": "not-a-cursor"}),
        (f"/groups/{group['id']}/members", {"limit": "0"}),
        ("/items", {"item_type": "not-an-item-type"}),
        (f"/items/{item['id']}/permissions", {"limit": "nope"}),
        (f"/items/{item['id']}/share-links", {"cursor": "bad"}),
        (f"/items/{item['id']}/comments", {"limit": "201"}),
        ("/search", {"q": "Query", "cursor": "bad"}),
        (f"/items/{item['id']}/activity", {"limit": "inf"}),
    ]:
        resp = client.get(path, query_string=query)
        assert resp.status_code == 400, (path, resp.get_data(as_text=True))
        body = resp.get_json()
        assert isinstance(body, dict)
        assert isinstance(body.get("error"), str)


def test_create_item_validates_item_specific_fields(tmp_path, monkeypatch):
    client = _build_client(tmp_path / "item_validation.db", monkeypatch)
    user = client.post(
        "/users", json={"email": "iv@example.com", "display_name": "Item Validator"}
    ).get_json()

    bad_doc = client.post(
        "/items",
        json={
            "name": "Bad Doc",
            "item_type": "doc",
            "owner_user_id": user["id"],
            "sheet_data": {"A1": "x"},
        },
    )
    assert bad_doc.status_code == 400

    bad_sheet = client.post(
        "/items",
        json={
            "name": "Bad Sheet",
            "item_type": "sheet",
            "owner_user_id": user["id"],
            "content_text": "not allowed",
        },
    )
    assert bad_sheet.status_code == 400

    bad_folder = client.post(
        "/items",
        json={
            "name": "Bad Folder",
            "item_type": "folder",
            "owner_user_id": user["id"],
            "content_text": "not allowed",
        },
    )
    assert bad_folder.status_code == 400

    bad_sheet_map = client.post(
        "/items",
        json={
            "name": "Bad Sheet Map",
            "item_type": "sheet",
            "owner_user_id": user["id"],
            "sheet_data": {"A1": 1},
        },
    )
    assert bad_sheet_map.status_code == 400

    sheet = client.post(
        "/items",
        json={
            "name": "Good Sheet",
            "item_type": "sheet",
            "owner_user_id": user["id"],
            "sheet_data": {"A1": "1"},
        },
    ).get_json()
    bad_update = client.put(
        f"/items/{sheet['id']}/content",
        json={"sheet_data": {"A1": 1}},
    )
    assert bad_update.status_code == 400


def test_permissions_validate_principal_id_rules(tmp_path, monkeypatch):
    client = _build_client(tmp_path / "perm_rules.db", monkeypatch)
    user = client.post(
        "/users", json={"email": "perm@example.com", "display_name": "Perm User"}
    ).get_json()
    doc = client.post(
        "/items",
        json={
            "name": "Perm Doc",
            "item_type": "doc",
            "owner_user_id": user["id"],
            "content_text": "hello",
        },
    ).get_json()

    anyone_bad = client.post(
        f"/items/{doc['id']}/permissions",
        json={"principal_type": "anyone", "principal_id": "unexpected", "role": "viewer"},
    )
    assert anyone_bad.status_code == 400

    user_missing = client.post(
        f"/items/{doc['id']}/permissions",
        json={"principal_type": "user", "role": "viewer"},
    )
    assert user_missing.status_code == 400

    user_ok = client.post(
        f"/items/{doc['id']}/permissions",
        json={"principal_type": "user", "principal_id": user["id"], "role": "viewer"},
    )
    assert user_ok.status_code == 201


def test_item_scoped_subresource_routes_return_404_for_missing_item(tmp_path, monkeypatch):
    client = _build_client(tmp_path / "missing_item.db", monkeypatch)
    missing = "missing-item-id"

    assert client.get(f"/items/{missing}/permissions").status_code == 404
    assert client.delete(f"/items/{missing}/permissions/perm-id").status_code == 404
    assert client.get(f"/items/{missing}/share-links").status_code == 404
    assert client.delete(f"/items/{missing}/share-links/link-id").status_code == 404
    assert client.get(f"/items/{missing}/comments").status_code == 404


def test_api_key_auth(tmp_path, monkeypatch):
    client = _build_client(
        tmp_path / "auth.db",
        monkeypatch,
        env={"GWSYNTH_API_KEY": "secret"},
    )

    assert client.get("/health").status_code == 200
    assert client.get("/users").status_code == 401

    ok = client.get("/users", headers={"Authorization": "Bearer secret"})
    assert ok.status_code == 200
